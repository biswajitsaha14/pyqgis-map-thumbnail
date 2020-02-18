"""
__author__ = Biswajit Saha
__email__= bsnayan@gmail.com

"""


from qgis.core import *
from qgis.gui import *
from qgis.utils import iface
from PyQt5.QtGui import QFont
from PyQt5.QtCore import *
#from PyQt5.QtGui import QColor
import seaborn as sns

import psycopg2
import psycopg2.extras
import sys
import os
import numpy as np
from collections import namedtuple
import pandas as pd
import seaborn as sns


class MapGrid:

    def __init__(self,ncols, nrows,**kwargs):
        self.ncols =ncols
        self.nrows = nrows
        self.paperWidth = 841
        self.paperHeight = 1189
        self.marginX = 10
        self.marginY = 10
        self.gapX = 10
        self.gapY = 10
        if kwargs:
            self.__dict__.update(kwargs)
   
    def create_grid(self):
        x=np.linspace(self.marginX,self.paperWidth-self.marginX*2,self.ncols, endpoint=False)
        y=np.linspace(self.marginY,self.paperHeight-self.marginY*2,self.nrows,endpoint=False)

        self.frameWidth = x[1]-x[0]-self.gapX
        self.frameHeight = y[1]-y[0]-self.gapY

        arrGapX = np.repeat(self.gapX,self.ncols )
        #arrGapX[0]=0
        arrGapY = np.repeat(self.gapY,self.nrows )
        #arrGapY[0]=0
        x = x+arrGapX
        y = y +arrGapY


        xx,yy = np.meshgrid(x,y)
        coords = np.c_[xx.ravel(),yy.ravel()]
        return coords.tolist()


def create_html_table(layout):
    df = pd.read_csv('mappingexample1/jobs_centres_clean.csv')
    colors=sns.color_palette('bright',5).as_hex()  
    
    centres = df['centrename'].unique().tolist()
    htlmlElmemts ={}
    for centre in centres:
        htmlString = "<table><tr><th>Job Sectors</th><th>Count</th></tr>"

        data_centre = df[df['centrename']==centre]
        for idx,row in data_centre.iterrows():
            htmlString +="<tr style='color:{};'><td>{}</td><td>{:,}</td></tr>".format(colors[row['cat_id']-1],row['broad_category'],row['people'])
        htmlString +="<tr><td>{}</td><td>{:,}</td></tr>".format('Total',data_centre['people'].sum())
        htmlString +="</table>"
        blockStatsHTML = QgsLayoutItemHtml.create(layout)
        # blockStatsFrame = QgsLayoutFrame(layout, blockStatsHTML)
        # blockStatsFrame.attemptSetSceneRect(QRectF(10, 10, 20, 30))
        # blockStatsFrame.setFrameEnabled(False)
        # blockStatsHTML.addFrame(blockStatsFrame)

        # set HTML contents
        blockStatsHTML.setContentMode(QgsLayoutItemHtml.ManualHtml)
        print(htmlString)

        htmlTemplate = """
        <!DOCTYPE html>
        <html>

        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                table {{
                    border-collapse: collapse;width: 100%;
                    font-family: Arial, Helvetica, sans-serif;
                }}

                th,
                td {{
                    padding:3px 0px;text-align: left;border-bottom: 1px solid #ddd;font-size: 12px;
                }}
            </style>
        </head>

        <body>
        {}

        </body>

        </html>
        """.format(htmlString)

              
        blockStatsHTML.setHtml(htmlTemplate)
        blockStatsHTML.loadHtml()
        htlmlElmemts[centre]= blockStatsHTML
    return htlmlElmemts




class GscDB:

    def __init__(self):
        self.params={
            'host':'localhost',
            'dbname':'gsc',
            'user':'biswajitsaha',
            'password':''
        }
        self.connection= psycopg2.connect(**self.params)
        self.cursor =self.connection.cursor(cursor_factory= psycopg2.extras.NamedTupleCursor)
    
    def excute_sql(self,sql):
        self.cursor.execute(sql)
        return self.cursor
    
    def get_params(self):
        return self.params
    
    def __del__(self):
        print('closing connetion')
        self.cursor.close()
        self.connection.close()



def initQgis():
    qgis_prefix = os.getenv("QGIS_PREFIX_PATH") 
    QgsApplication.setPrefixPath(qgis_prefix,True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    return qgs




def create_memory_layer(layername, fields):
    mem_layer = QgsVectorLayer(f"polygon?{fields}", "No. of Centre \nWorkers by SA1", "memory")
    crs = QgsCoordinateReferenceSystem(28356)
    print(crs)

    mem_layer.setCrs(crs)
    
    return mem_layer


def applyCustomGraduateSymbol(layer,targetField):

    class_breaks= [
        [1,10],
        [11,20],
        [21,30],
        [31,40],
        [41,50],
        [51,1500]

    ]
    n_class =len(class_breaks)

    colors= sns.color_palette('Blues', n_class+3).as_hex()[2:]
    rangeList =[]
    for idx,class_break in enumerate(class_breaks):
        lowerValue, upperValue =class_break
        props ={}
        props['color']=colors[idx]
        props['outline_width']='0.00'
        props['outline_color'] = '#ffffff'
        symbol= QgsFillSymbol.createSimple(props)
        myRange =QgsRendererRange(float(lowerValue),float(upperValue),symbol,'{}-{}'.format(lowerValue,upperValue)if lowerValue<=50 else '50+')
        rangeList.append(myRange)
    myRenderer = QgsGraduatedSymbolRenderer(targetField, rangeList)  
    myRenderer.setMode(QgsGraduatedSymbolRenderer.Custom)               

    layer.setRenderer(myRenderer)   


app = initQgis()

db = GscDB()

project = QgsProject()

cursor = db.excute_sql("SELECT centrename, centretype from centres")
centres = [centre for centre in cursor.fetchall()]

grid = MapGrid(5,8)
mapPos = grid.create_grid()
layout = QgsPrintLayout(project)
layoutName = 'test_layout'

htmlTables=create_html_table(layout)
#layout.setName(layoutName)
layout.initializeDefaults()
page = layout.pageCollection().pages()[0]
page.setPageSize(QgsLayoutSize(grid.paperWidth, grid.paperHeight))
layers={}

basedir = '/Users/biswajitsaha/Kitchen/dev/pyqgis/geopakages/basemaps.gpkg'
baselayer_roads  = QgsVectorLayer(basedir+"|layername={}".format('roads'),"roads", "ogr")
baselayer_roads.loadNamedStyle('/Users/biswajitsaha/Kitchen/dev/pyqgis/mappingexample1/road.qml')
baselayer_roads.setOpacity(.80)

baselayer_ocean  = QgsVectorLayer(basedir+"|layername={}".format('ocean'),"ocean", "ogr")
baselayer_ocean.loadNamedStyle('/Users/biswajitsaha/Kitchen/dev/pyqgis/mappingexample1/ocean.qml')
#baselayer_ocean.setOpacity(.50)

baselayer_mua  = QgsVectorLayer(basedir+"|layername={}".format('mua'),"mua", "ogr")
baselayer_mua.loadNamedStyle('/Users/biswajitsaha/Kitchen/dev/pyqgis/mappingexample1/mua.qml')

baselayer_ops  = QgsVectorLayer(basedir+"|layername={}".format('openspace'),"openspace", "ogr")
baselayer_ops.loadNamedStyle('/Users/biswajitsaha/Kitchen/dev/pyqgis/mappingexample1/openspace.qml')
# baselayer_ops.setOpacity(.50)

baselayer_centre  = QgsVectorLayer(basedir+"|layername={}".format('centres'),"centres", "ogr")
baselayer_centre.loadNamedStyle('/Users/biswajitsaha/Kitchen/dev/pyqgis/mappingexample1/centre.qml')

# baselayer_railways  = QgsVectorLayer(basedir+"|layername={}".format('railways'),"railways", "ogr")
# baselayer_railways.loadNamedStyle('/Users/biswajitsaha/Kitchen/dev/pyqgis/mappingexample1/railways.qml')
#baselayer_roads.triggerRepaint()
legends={}
root = QgsLayerTree()
centre_layers={}

for idx,centre in enumerate(centres):
    c= centre.centrename

    root.clear()
    baselayer_centre.setSubsetString('"centrename"=\'%s\'' % c)
    centre_layers[c]= baselayer_centre.clone()
    baselayer_centre.setSubsetString('')

    
    centrename =c
    layer_catchment_name = 'service area {}'.format(centrename)
    layer_catchment_fields = 'field= centrename:string &field=sa1_id:string&field=jobs:integer'


    crs = QgsCoordinateReferenceSystem(28356)
    #baselayer_roads.setCrs(crs)

    #baselayer_roads.loadNamedStyleFromDatabase(style_doc)

    layer = create_memory_layer(layer_catchment_name,layer_catchment_fields)
  

   
    sql = """
        SELECT st_astext(s.geom) geom, s."sa1_7dig16" sa1_id,c.centrename centrename, c.totaljobs jobs  from sa1 s 
        inner join centre_workers c on s.sa1_7dig16= c.sa1_7dig16
        where c.centrename='{}'and c.totaljobs>0
    
        """.format(centrename)
    cursor = db.excute_sql(sql)
    rows = cursor.fetchall()
    dp = layer.dataProvider()
    for row in rows:
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromWkt(row.geom))
        feature.setAttributes([row.centrename, row.sa1_id,row.jobs])
        dp.addFeature(feature)
    layer.updateExtents()
    print(layer.featureCount())

    applyCustomGraduateSymbol(layer,'jobs')
    layer.triggerRepaint()
    layers[centrename]=layer

    x,y = mapPos[idx]


    mapFrameWidth = grid.frameWidth-40
    mymap = QgsLayoutItemMap(layout)
    mymap.setRect(20,20,20,20)
    mymap.setExtent(QgsRectangle(layers[centrename].extent()))
    mymap.setFrameEnabled(True)
    mymap.setFrameStrokeWidth(QgsLayoutMeasurement(0.10, QgsUnitTypes.LayoutMillimeters))
    mymap.setLayers([centre_layers[centrename],baselayer_roads,layers[centrename],baselayer_mua,baselayer_ocean])
    mymap.setKeepLayerSet(True)
    mymap.setKeepLayerStyles(True)
    layout.addLayoutItem(mymap)
    mymap.attemptMove(QgsLayoutPoint(x,y,QgsUnitTypes.LayoutMillimeters))
    mymap.attemptResize(QgsLayoutSize( mapFrameWidth,grid.frameHeight,QgsUnitTypes.LayoutMillimeters))
    infoStartX = x+mapFrameWidth+2
    infoStartInitialY= y

    title = QgsLayoutItemLabel(layout)
    if centrename=='Western Sydney Airport and Badgerys Creek Aerotropolis':
        title.setText('Western Sydney Airport')
        # title.attemptResize(QgsLayoutSize(20,20,QgsUnitTypes.LayoutMillimeters))
        # subtitlePos= infoStartInitialY+6
    else:
       
        title.setText(centrename)

    subtitlePos= infoStartInitialY+3
    #title.setText(centrename)
    title.setFont(QFont("Arial", 10,QFont.Bold))
    title.adjustSizeToText()
    layout.addLayoutItem(title)
    title.attemptMove(QgsLayoutPoint(infoStartX, infoStartInitialY, QgsUnitTypes.LayoutMillimeters))

    subtitle = QgsLayoutItemLabel(layout)
    subtitle.setText(centre.centretype)
    subtitle.setFont(QFont("Arial", 7))
    subtitle.adjustSizeToText()
    layout.addLayoutItem(subtitle)
    subtitle.attemptMove(QgsLayoutPoint(infoStartX, subtitlePos, QgsUnitTypes.LayoutMillimeters))

    #adding chart
    infoStartInitialY +=10
    chart = QgsLayoutItemPicture(layout)
    
    chart.setPicturePath('/Users/biswajitsaha/Kitchen/dev/pyqgis/mappingexample1/piecharts/{}.png'.format(centrename))
    
    chart.setId('chart {}'.format(centrename))
    layout.addItem(chart)
    chart.attemptResize(QgsLayoutSize(30,30,QgsUnitTypes.LayoutMillimeters))
    chart.attemptMove(QgsLayoutPoint(infoStartX, infoStartInitialY, QgsUnitTypes.LayoutMillimeters))

    
    
    
    
    infoStartInitialY +=32

    table=htmlTables[centrename]
    blockStatsFrame = QgsLayoutFrame(layout, table)
    blockStatsFrame.attemptSetSceneRect(QRectF(10, 10, 35, 80))
    blockStatsFrame.setFrameEnabled(False)
    table.addFrame(blockStatsFrame)
    blockStatsFrame.attemptMove(QgsLayoutPoint(infoStartX, infoStartInitialY, QgsUnitTypes.LayoutMillimeters))
    
    


    legend = QgsLayoutItemLegend(layout)
    #legend.setTitle("Legend")
   

    # layer = project.mapLayersByName('sa1')[0]

    root.addLayer(layers[centrename])
    legend.model().setRootGroup(root)
    #legend.cleanup()
    
    infoStartInitialY +=53
    legend.attemptMove(QgsLayoutPoint(infoStartX, infoStartInitialY, QgsUnitTypes.LayoutMillimeters))

    #changing fontstyle
    newFont = QFont("Arial", 7)
    legend.setStyleFont(QgsLegendStyle.Title, newFont)
    legend.setStyleFont(QgsLegendStyle.Subgroup, newFont)
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, newFont)
    legend.setSymbolHeight(2)
    legend.setSymbolWidth(2)
    legend.setWrapString('\n')
    legend.setBoxSpace(0.0)
    
    #legends[centrename]= legend
    print(centrename)
    #legend.setLinkedMap(mymap)
    #legend.refresh()
    layout.addLayoutItem(legend)
    legend.updateLegend()


layout.refresh()
exporter = QgsLayoutExporter(layout)
exportSettings = QgsLayoutExporter.PdfExportSettings()
exportSettings.dpi=300
exportSettings.rasterizeWholeImage=False
exporter.exportToPdf("/Users/biswajitsaha/Kitchen/dev/pyqgis/workers_by_centre_A0.pdf", exportSettings)
# project =QgsProject.instance()
# project.addMapLayer(layer, True)

# mapcanvas = QgsMapCanvas()
# mapcanvas.setCanvasColor(Qt.white)
# mapcanvas.enableAntiAliasing(True)
# mapcanvas.setExtent(layer.extent())
# mapcanvas.setLayers([layer,baselayer_roads])
# mapcanvas.show()

print('done')
