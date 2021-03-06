# -*- coding: utf-8 -*-

"""
***************************************************************************
    SumLines.py
    ---------------------
    Date                 : August 2012
    Copyright            : (C) 2012 by Victor Olaya
    Email                : volayaf at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Victor Olaya'
__date__ = 'August 2012'
__copyright__ = '(C) 2012, Victor Olaya'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os

from qgis.PyQt.QtGui import QIcon

from qgis.core import QgsFeature, QgsGeometry, QgsFeatureRequest, QgsDistanceArea

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterVector
from processing.core.parameters import ParameterString
from processing.core.outputs import OutputVector
from processing.tools import dataobjects, vector

pluginPath = os.path.split(os.path.split(os.path.dirname(__file__))[0])[0]


class SumLines(GeoAlgorithm):

    LINES = 'LINES'
    POLYGONS = 'POLYGONS'
    LEN_FIELD = 'LEN_FIELD'
    COUNT_FIELD = 'COUNT_FIELD'
    OUTPUT = 'OUTPUT'

    def getIcon(self):
        return QIcon(os.path.join(pluginPath, 'images', 'ftools', 'sum_lines.png'))

    def defineCharacteristics(self):
        self.name, self.i18n_name = self.trAlgorithm('Sum line lengths')
        self.group, self.i18n_group = self.trAlgorithm('Vector analysis tools')

        self.addParameter(ParameterVector(self.LINES,
                                          self.tr('Lines'), [ParameterVector.VECTOR_TYPE_LINE]))
        self.addParameter(ParameterVector(self.POLYGONS,
                                          self.tr('Polygons'), [ParameterVector.VECTOR_TYPE_POLYGON]))
        self.addParameter(ParameterString(self.LEN_FIELD,
                                          self.tr('Lines length field name', 'LENGTH')))
        self.addParameter(ParameterString(self.COUNT_FIELD,
                                          self.tr('Lines count field name', 'COUNT')))

        self.addOutput(OutputVector(self.OUTPUT, self.tr('Line length')))

    def processAlgorithm(self, progress):
        lineLayer = dataobjects.getObjectFromUri(self.getParameterValue(self.LINES))
        polyLayer = dataobjects.getObjectFromUri(self.getParameterValue(self.POLYGONS))
        lengthFieldName = self.getParameterValue(self.LEN_FIELD)
        countFieldName = self.getParameterValue(self.COUNT_FIELD)

        (idxLength, fieldList) = vector.findOrCreateField(polyLayer,
                                                          polyLayer.fields(), lengthFieldName)
        (idxCount, fieldList) = vector.findOrCreateField(polyLayer, fieldList,
                                                         countFieldName)

        writer = self.getOutputFromName(self.OUTPUT).getVectorWriter(
            fieldList.toList(), polyLayer.wkbType(), polyLayer.crs())

        spatialIndex = vector.spatialindex(lineLayer)

        ftLine = QgsFeature()
        ftPoly = QgsFeature()
        outFeat = QgsFeature()
        inGeom = QgsGeometry()
        outGeom = QgsGeometry()
        distArea = QgsDistanceArea()

        features = vector.features(polyLayer)
        total = 100.0 / len(features)
        hasIntersections = False
        for current, ftPoly in enumerate(features):
            inGeom = ftPoly.geometry()
            attrs = ftPoly.attributes()
            count = 0
            length = 0
            hasIntersections = False
            lines = spatialIndex.intersects(inGeom.boundingBox())
            if len(lines) > 0:
                hasIntersections = True

            if hasIntersections:
                for i in lines:
                    request = QgsFeatureRequest().setFilterFid(i)
                    ftLine = lineLayer.getFeatures(request).next()
                    tmpGeom = ftLine.geometry()
                    if inGeom.intersects(tmpGeom):
                        outGeom = inGeom.intersection(tmpGeom)
                        length += distArea.measure(outGeom)
                        count += 1

            outFeat.setGeometry(inGeom)
            if idxLength == len(attrs):
                attrs.append(length)
            else:
                attrs[idxLength] = length
            if idxCount == len(attrs):
                attrs.append(count)
            else:
                attrs[idxCount] = count
            outFeat.setAttributes(attrs)
            writer.addFeature(outFeat)

            progress.setPercentage(int(current * total))

        del writer
