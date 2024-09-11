import numpy as np
import scipy.io as sio
from bokeh.plotting import figure, curdoc, show
from bokeh.models import ColumnDataSource, Button, CustomJS, Slider, ColorBar, LogColorMapper, Div, Text, LogTicker, RangeSlider, Select
from bokeh.layouts import column, row, layout
import time
import labrad
import yaml
from datetime import datetime
import os
import glob
import logging



#Parameter Definitions
params = dict()

params['ROOTDIR'] = r"C:\Users\Marconi\Young Lab Dropbox\Young Group\THz\Raw Data"                               
params['DATADIR'] = "2024_08_20_AKNDB32_2B"  
params['FILENAME1'] = "Spectrum_1D"
params['FILENAME2'] = "Spectrum_2D"


params["SpectroUPD"] = 10 #in seconds

#Spectrogram time points (too many will cause lag) 
params["specxres"]= 200

params["avgs"] = 5
params["lgscale"] = 1e-3
params["freqspan"] = 390
params["freqstart"] = 0

SPANS = {0:0.191,
              1:0.382,
              2:0.763,
              3:1.5,
              4:3.1,
              5:6.1,
              6:12.2,
              7:24.4,
              8:48.75,
              9:97.5,
              10:195.0,
              11:390.0,
              12:780.0,
              13:1560.0,
              14:3120.0,
              15:6250.0,
              16:12500.0,
              17:25000.0,
              18:50000.0,
              19:100000.0}
SPANS_REVERSED = {
    0.191: 0,
    0.382: 1,
    0.763: 2,
    1.5: 3,
    3.1: 4,
    6.1: 5,
    12.2: 6,
    24.4: 7,
    48.75: 8,
    97.5: 9,
    195.0: 10,
    390.0: 11,
    780.0: 12,
    1560.0: 13,
    3120.0: 14,
    6250.0: 15,
    12500.0: 16,
    25000.0: 17,
    50000.0: 18,
    100000.0: 19
}

#Class for instance of labrad
class Spectrum_Live:
    '''
    A GUI for the sr770 with live spectrums
    '''
    def __init__(self, sr770, dv, document):
        self.sr770 = sr770
        self.dv = dv
        self.rootdir = params['ROOTDIR']
        self.datadir = params['DATADIR']
        self.datapath = self.rootdir+"\\"+self.datadir+".dir"

        self.uploop = None
        self.docu = document
        self.updatecounter = 0
        self.imgdata = np.empty((400,params["specxres"]))
        self.timedata = np.empty(params["specxres"])
        self.avg = np.empty((400,params["avgs"]))

    def updatemain(self):
        l = [0,0]
        try:
            l = self.sr770.readpsdout(-1)
            new = dict()
            new['x'] = l[:,0]
            new['y']= l[:,1]
            ds.data = new
        except Exception as e:
            print("Error occured in reading the psd from the SR770%s"%e)
        
        #if(params['avgon']):  
        #else:
        #    self.avg = np.hstack((np.delete(self.avg,0,1),np.array(ds.data['y'], copy=False, subok=True, ndmin=2).T))

    def updatespectrogr(self):
        self.imgdata = np.hstack((np.delete(self.imgdata,0,1),np.array(ds.data['y'], copy=False, subok=True, ndmin=2).T))
        spgrds.data['values'] = [self.imgdata]

    def activatetog(self):
        if(self.uploop == None):
            activate.label = "Deactivate"
            self.uploop = self.docu.add_periodic_callback(self.updatemain, 300)
            self.uploopspg = self.docu.add_periodic_callback(self.updatespectrogr, 600)
        else:
            self.docu.remove_periodic_callback(self.uploop)
            self.docu.remove_periodic_callback(self.uploopspg)
            activate.label = "Activate"
            self.uploop = None
            self.uploopspg = None

#Function Definitions
def init_labrad():
    cxn = labrad.connect()
    sr770 = ''
    dv = ''
    try: 
        sr770 = cxn.signal_analyzer_sr770()
        sr770.select_device()
        sr770.set_timeout_gpib(0.1) #set the GPIB timeout to 100ms

        params["freqspan"] = SPANS[SPANS_REVERSED[sr770.span()['Hz']]] #translate the spans into proper text format. 

        params["freqstart"] = sr770.start_frequency()['Hz']
    except Exception as e:
        print("Failed to connect to server sr770.")
        print(e)

    try: 
        dv = cxn.data_vault()
        #dv.cd(params['DATADIR'])
    except Exception as e:
        print("Failed to connect to server datavault.")
        print(e)
    
    return Spectrum_Live(sr770, dv, curdoc())

sr770gui = init_labrad()

#Spectrogram with colorbar
p2 = figure(title="Spectrogram", x_axis_label='Time', y_axis_label='Frequency',toolbar_location="above")
initdat1 = { "values" : [np.empty((400,params["specxres"]))]}
spgrds = ColumnDataSource(initdat1)
SpectroGramColor = LogColorMapper(low=1e-7,high=params["lgscale"],palette="Viridis256")
sprg_ima = p2.image(image="values", x=0, y=params["freqstart"], dw=params["specxres"], dh=params["freqspan"],source=spgrds,color_mapper=SpectroGramColor)
color_bar = ColorBar(color_mapper=SpectroGramColor, ticker=LogTicker(),
                     label_standoff=12, border_line_color=None, location=(0,0))

p2.add_layout(color_bar, 'right')

#Spectrum straight.
p1 = figure(title="Spectrum", x_axis_label='Frequency', y_axis_label='dbV',y_axis_type="log")
initdat2 = {'x':[1], 'y': [2]}
ds = ColumnDataSource(initdat2)
r = p1.line(x='x',y='y',source=ds)

activate = Button(label="Activate", aspect_ratio=2)
activate.on_event('button_click', sr770gui.activatetog)

save = Button(label="Save (Does not work)")
#need to implement dv save feature.




spectroslider = RangeSlider(start=-7, end=7, value=[-5,-3], step=.1, title="Color Map Range exponent")
spectroslider.js_on_change('value',
    CustomJS(args=dict(other=SpectroGramColor),
             code="other.high = 10**(this.value[1]); other.low = 10**(this.value[0])"
    )
)

SpectroDiv = Div(text="""Change the color scale of the spectrograph.""",
width=200, height=100)
spectrogrsets = column([SpectroDiv,spectroslider])


# Create the controls box
title_div = Div(text="<h2>Controls</h2>", styles={'font-size': '16pt', 'font-weight': 'bold'})

# Create buttons
Spans = Select(name="Span", value = params["freqspan"],options=[
    "191mHz",
    "382mHz",
    "763mHz",
    "1.5Hz",
    "3.1Hz",
    "6.1Hz",
    "12.2Hz",
    "24.4Hz",
    "48.75Hz",
    "97.5Hz",
    "195Hz",
    "390Hz",
    "780Hz",
    "1.56KHz",
    "3.125KHz",
    "6.25KHz",
    "12.5KHz",
    "25KHz",
    "50KHz",
    "100KHz"
])
button2 = Button(label="start freq")
button3 = Button(label="center freq")
button4 = Button(label="autoy-scale")
button5 = Button(label="autorange: Off")

button6 = Button(label="averaging")
button7 = Button(label="save")
button8 = Button(label="Local Mode (need to deactivate)")

#Create functions for callback on button and spans

possiblespans={
    "191mHz": 0,
    "382mHz": 1,
    "763mHz": 2,
    "1.5Hz": 3,
    "3.1Hz": 4,
    "6.1Hz": 5,
    "12.2Hz": 6,
    "24.4Hz": 7,
    "48.75Hz": 8,
    "97.5Hz": 9,
    "195Hz": 10,
    "390Hz": 11,
    "780Hz": 12,
    "1.56KHz": 13,
    "3.125KHz": 14,
    "6.25KHz": 15,
    "12.5KHz": 16,
    "25KHz": 17,
    "50KHz": 18,
    "100KHz": 19
}

def span(attr, old, new):
    try:
        sr770gui.sr770.span(possiblespans[new])
        params["freqspan"] = SPANS[possiblespans[new]]
    except KeyError as e:
        print("Error setting the span, span not found: %s"%e)
    except Exception as l:
        print("Error setting the span: %s"%l)

def autoy_scale():
    sr770gui.sr770.autoscale(-1)

def autorange():
    if(button5.label[-3:]=="Off"):
        sr770gui.sr770.autorange(1)
        button5.label = "autorange: On"
    else:
        sr770gui.sr770.autorange(0)
        button5.label = "autorange: Off"
def localactivate():
    sr770gui.sr770.gpib_write("LOCL0")

# Attach callbacks to buttons
Spans.on_change('value',span)
#button2.on_click(start_freq)
#button3.on_click(center_freq)
button4.on_click(autoy_scale)
button5.on_click(autorange)

#button6.on_click(averaging)
#button7.on_click()
button8.on_click(localactivate)

# Create columns for buttons
column1 = layout([Spans, button4], [button2, button5], [button3],sizing_mode="scale_both")
column2 = column(button6, button7, button8)


settingswidgets = layout(
    [
        [activate, column2],
        [column1, spectrogrsets]
    ]
,sizing_mode="scale_both")

lay = layout(
    [settingswidgets,p1],
    [p2],
sizing_mode="scale_both")


sr770gui.docu.add_root(lay)



