import numpy as np
import scipy.io as sio

from bokeh.plotting import figure, curdoc, show
from bokeh.models import ColumnDataSource, Button, CustomJS, Slider, ColorBar, LogColorMapper, Div, Text, LogTicker, RangeSlider, Select, Range1d, TextInput
from bokeh.layouts import column, row, layout

from collections import deque
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
params['DATADIR'] = "2024_09_09_TL2714_ESP302"  
params['FILENAME1'] = "Spectrum_1D"
params['FILENAME2'] = "Spectrum_2D"


params["SpectroUPD"] = 10 #in seconds

#Spectrogram time points (too many will cause lag) 
params["specxres"]= 1000

params["avgs"] = 5
params["lgscale"] = 1e-3
params["freqspan"] = 390
params["freqstart"] = 0

#Change later so that vscode can autocomplete variable names for now
# Load config file
#CONFIG_FILENAME = 'SpectrumLive.yml'

#with open(os.path.realpath(CONFIG_FILENAME),'r') as f:
#    params = yaml.safe_load(f)

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
        self.dequeimage = deque(np.empty((params["specxres"],400)))
        self.timedata = deque(np.empty(params["specxres"]))
        self.avg = deque(np.empty((params["avgs"],400)))
        self.lastupdatetime = time.time()

    def updatemain(self):
        l = [0,0]
        
        try:
            if(self.sr770.poll_FFT()):
                l = self.sr770.readpsdout(-1)
                new = dict()
                new['x'] = l[:,0]
                new['y']= l[:,1]
                ds.data = new
                self.lastupdatetime = time.time()
            else:
                return
        except Exception as e:
            print("Error occured in reading the psd from the SR770%s"%e)
        
        #if(params['avgon']):  
        #else:
        #    self.avg = np.hstack((np.delete(self.avg,0,1),np.array(ds.data['y'], copy=False, subok=True, ndmin=2).T))

    def updatespectrogr(self):
        self.dequeimage.popleft()
        self.dequeimage.append(np.array(ds.data['y']).T)
        #self.imgdata = np.hstack((np.delete(self.imgdata,0,1),np.array(ds.data['y'], copy=False, subok=True, ndmin=2).T))
        spgrds.data['values'] = [np.array(self.dequeimage).T]
        self.timedata = np.roll(self.timedata,1)

    def resetSpectro(self):
         self.dequeimage = deque(np.empty((params["specxres"],400)))

    def activatetog(self):
        if(self.uploop == None):
            activate.label = "Deactivate"
            self.uploop = self.docu.add_periodic_callback(self.updatemain, 100)
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
        dv.cd(params['DATADIR'])
    except Exception as e:
        print("Failed to connect to server datavault.")
        print(e)
    
    return Spectrum_Live(sr770, dv, curdoc())

sr770gui = init_labrad()

#Spectrogram with colorbar
TOOLTIPS = [
    ("x", "$x"),
    ("y", "$y"),
    ("value", "@values"),
]
SPCGraph = figure(title="Spectrogram", x_axis_label='Time', y_axis_label='Frequency',toolbar_location="above",tooltips=TOOLTIPS)
SPCGraph.min_border_left = 0
SPCGraph.min_border_right = 0
SPCGraph.min_border_top = 0
SPCGraph.min_border_bottom = 0
initdat1 = { "values" : [np.empty((400,params["specxres"]))], "freqstart":[params["freqstart"]],"specxres":[params["specxres"]],"freqspan":[params["freqspan"]]}
spgrds = ColumnDataSource(initdat1)
SpectroGramColor = LogColorMapper(low=1e-7,high=params["lgscale"],palette="Viridis256")
sprg_ima = SPCGraph.image(image="values", x=0, y="freqstart", dw='specxres', dh="freqspan",source=spgrds,color_mapper=SpectroGramColor)

#color bar for spectrogram
color_bar = ColorBar(color_mapper=SpectroGramColor, ticker=LogTicker(),
                     label_standoff=12, border_line_color=None, location=(0,0))
SPCGraph.add_layout(color_bar, 'right')

#Spectrum graph itself..
SPCTRMGraph = figure(title="Spectrum", x_axis_label='Frequency', y_axis_label='dbV',y_axis_type="log")
initdat2 = {'x':[1], 'y': [2]}
ds = ColumnDataSource(initdat2)
r = SPCTRMGraph.line(x='x',y='y',source=ds)





spectroslider = RangeSlider(start=-7, end=7, value=[-7,-3], step=.1, title="Color Map Range exponent")
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
startfreqbutt = Button(label="Update Start Freq")
startfreqinput = TextInput(value="Type here")
centerfreqbutt = Button(label="Update Center Freq")
centerfreqinput = TextInput(value="Type here")

Spanstext = Div(text="<b>Set the Span</b>", width=100, height=100)


freqcontrol1 = row([startfreqbutt, startfreqinput], sizing_mode="scale_both")
freqcontrol2 = row([centerfreqbutt, centerfreqinput],sizing_mode="scale_both")
freqcontrol3 = row([Spanstext, Spans], sizing_mode="scale_both")

button4 = Button(label="autoy-scale")
button5 = Button(label="autorange: Off")

button6 = Button(label="averaging")
button7 = Button(label="save")
button8 = Button(label="Local Mode (need to deactivate)")
activate = Button(label="Activate", aspect_ratio=2)
save = Button(label="Save (Does not work)")

#need to implement dv save feature.
#Create functions for callback on button and spans


def span(attr, old, new):
    try:
        sr770gui.sr770.span(possiblespans[new])
        params["freqspan"] = SPANS[possiblespans[new]]
        params["freqstart"] = ds.data['x'][0]
        sr770gui.resetSpectro()
        sprg_ima.glyph.update(y = params["freqstart"],dh=params["freqspan"])
        #SPCGraph.y_range = Range1d( params["freqstart"], params['freqstart']+params["freqspan"])

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

def startfreq():
    sr770gui.sr770.
# Attach callbacks to buttons
Spans.on_change('value',span)
startfreqbutt.on_click(start_freq)
centerfreqbutt.on_click(center_freq)
button4.on_click(autoy_scale)
button5.on_click(autorange)
activate.on_click(sr770gui.activatetog)

#button6.on_click(averaging)
#button7.on_click()
button8.on_click(localactivate)

# Create columns for buttons
column1 = layout(freqcontrol3, freqcontrol1, freqcontrol2, [button5, button4],sizing_mode="scale_both")
column2 = column(button6, button7, button8)


settingswidgets = layout(
    [
        [activate, column2],
        [column1, spectrogrsets]
    ]
,sizing_mode="scale_both")

lay = layout(
    [settingswidgets,SPCTRMGraph],
    [SPCGraph],
sizing_mode="scale_both")


sr770gui.docu.add_root(lay)



