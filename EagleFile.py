#!/usr/bin/python
import xml.dom.minidom as dom


def extractAttributeDict(xmlel):
    attr = dict()
    for el in xmlel.getElementsByTagName("attribute"):
        attr[el.getAttribute("name")] = el.getAttribute("value")
    return attr


class Device:
    def __init__(self, xmlel, deviceset):
        self.name = xmlel.getAttribute("name")
        self.deviceset = deviceset
        self.attr = extractAttributeDict(xmlel)

    def getAttributes(self):
        result = self.deviceset.getAttributes().copy()
        result.update(self.attr)
        return result

class DeviceSet:
    def __init__(self, xmlel):
        self.name = xmlel.getAttribute("name")
        self.attr = extractAttributeDict(xmlel)
        self.devices = dict()
        for el in xmlel.getElementsByTagName("device"):
            d = Device(el, self)
            self.devices[d.name] = d

    def getAttributes(self):
        return self.attr


class Part:
    def __init__(self, xmlel, device_sets):
        self.xmlel = xmlel
        self.name = xmlel.getAttribute("name")
        self.attr = extractAttributeDict(xmlel)
        for a in ["name", "value", "library", "deviceset", "device"]:
            self.attr[a] = xmlel.getAttribute(a)
        self.device = device_sets[self.attr["deviceset"]].devices[self.attr["device"]]
        self.sheets = []

    def include_in_bom(self):
        a = self.getAttributes()
        if ("EXCLUDE_FROM_BOM" in a) and (a["EXCLUDE_FROM_BOM"]=="YES"):
            return False
        else:
            return True

    def getAttributes(self):
        result = self.device.getAttributes().copy()
        result.update(self.attr)
        return result

    def getAttribute(self, attr):
        a = self.getAttributes()
        if attr in a:
            return a[attr]
        else:
            return ""

    def setAttribute(self, attr, value):

        self.attr[attr] = value

        if attr in ["value"]:
            self.xmlel.setAttribute(attr, value)
        else:
            # only have a attribute element if the attribute is not inherited with the same value
            inherited_props = self.device.getAttributes()
            if (attr in inherited_props) and (inherited_props[attr]==value):
                for el in self.xmlel.getElementsByTagName("attribute"):
                    if el.getAttribute("name")==attr:
                        self.xmlel.removeChild(el)
                        return
            else:
                for el in self.xmlel.getElementsByTagName("attribute"):
                    if el.getAttribute("name") == attr:
                        el.setAttribute("value", value)
                        return
                attrel = self.xmlel.ownerDocument.createElement("attribute");
                attrel.setAttribute("name", attr)
                attrel.setAttribute("value", value)
                self.xmlel.appendChild(attrel)

    def addSheet(self, sheetnum):
        if not sheetnum in self.sheets:
            self.sheets.append(sheetnum)
            self.sheets.sort()

    def getSheetsString(self):
        return ", ".join(str(x) for x in self.sheets)

    def __str__(self):
        return self.attr["name"] + " " + self.attr["value"]

class BoardElement:
    def __init__(self, xmlel):
        self.xmlel = xmlel
        self.attr = extractAttributeDict(xmlel)
        self.name = xmlel.getAttribute("name")

    def setAttribute(self, attr, value):
        self.attr[attr] = value

        if attr in ["value"]:
            self.xmlel.setAttribute(attr, value)
        else:
            for el in self.xmlel.getElementsByTagName("attribute"):
                if el.getAttribute("name") == attr:
                    el.setAttribute("value", value)
                    return
            attr_node = self.xmlel.ownerDocument.createElement("attribute");
            attr_node.setAttribute("name", attr)
            attr_node.setAttribute("value", value)
            attr_node.setAttribute("layer", "27")
            attr_node.setAttribute("display", "off")
            self.xmlel.appendChild(attr_node)

class EagleBoard:
    def __init__(self):
        self.xml = None
        self.boardElements = dict()

    def clear(self):
        self.boardElements.clear()

    def isEmpty(self):
        return len(self.boardElements.keys())==0

    def loadFile(self, filename):
        self.xml = dom.parse(filename)
        self.boardElements.clear()
        for el in self.xml.getElementsByTagName("element"):
            brd_element = BoardElement(el)
            self.boardElements[brd_element.name] = brd_element

    def saveToFile(self, filename):
        f = open(filename, 'wb')
        f.write(self.xml.toxml(encoding='utf-8'))
        f.close()

    def setAttribute(self, elementName, name, value):
        if elementName in self.boardElements:
            self.boardElements[elementName].setAttribute(name, value)

class EagleSchema:
    def __init__(self):
        self.xml = None
        self.device_sets = dict()
        self.parts = dict()
        self.bom = []

    def loadFile(self, filename):

        self.xml = dom.parse(filename)
        self.device_sets.clear()
        self.parts.clear()
        self.bom.clear()

        for el in self.xml.getElementsByTagName("deviceset"):
            ds = DeviceSet(el)
            self.device_sets[ds.name] = ds

        for el in self.xml.getElementsByTagName("part"):
            p = Part(el, self.device_sets)
            self.parts[p.name] = p
            if (p.include_in_bom()):
                self.bom.append(p)

        sheetnum = 0
        for sheetel in self.xml.getElementsByTagName("sheet"):
            sheetnum += 1
            for el in sheetel.getElementsByTagName("instance"):
                self.parts[el.getAttribute("part")].addSheet(sheetnum)

        self.bom.sort(key=lambda x: [x.attr["deviceset"], x.device.name, x.attr["value"], x.getSheetsString()])


    def saveToFile(self, filename):
        f = open(filename, 'wb')
        f.write(self.xml.toxml(encoding='utf-8'))
        f.close()