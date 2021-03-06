# ############################################################
# python class that runs experiments and save data
# author  Federico Corradi - federico.corradi@inilabs.com
# author  Diederik Paul Moeys - diederikmoeys@live.com
# ############################################################
from __future__ import division
import numpy as np
import matplotlib
from pylab import *
import time, os
import shutil
import caer_communication

''' 
If in the dark room set to true. This will always be the case as no measurement, 
apart from PTC, can be done outside of the dark room. Set to False if you want 
to run PTC outside to get conversion gain or just do dark measurement (where no 
setup is needed).
'''
dark_room = True
if(dark_room):
    import gpio_usb

###############################################################################
# CAMERA AND TEST SELECTION
###############################################################################
camera_file = 'cameras/davis208_parameters.txt'

do_set_bias = False

do_contrast_sensitivity = False # And DVS-FPN too
do_ptc = False
do_frequency_response = True
do_latency = False


do_latency_pixel_with_fiber = False
do_oscillations = False

###############################################################################
# PARAMETERS
###############################################################################
info = np.genfromtxt(camera_file, dtype='str')
sensor = info[0]
sensor_type = info[1]
bias_file = info[2]
if(info[3] == 'False'):
    dvs128xml = False
elif(info[3] == 'True'):
    dvs128xml == True
host_ip = info[4]
current_date = time.strftime("%d_%m_%y-%H_%M_%S")
datadir = 'measurements/Measurements'

if(do_set_bias):
    dvs_use = True; # If false use APS

if(do_contrast_sensitivity):
    sine_freq = 1 # contrast sensitivity/threshold
    oscillations = 10.0   # number of complete oscillations for contrast sensitivity/latency/oscillations    
    #contrast_base_levels = [200.0,2000.0] #contrast sensitivity base level sweeps
    contrast_base_levels = [1000.0]
    contrast_level = [0.5]#[0.1, 0.3, 0.5, 0.8] # contrast sensitivity
    # These thresholds are indexed together: they must be the same length and coherent (no off-on inversion!)
    onthr=[0 for x in range(len(info[12].split(',')))]
    for x in range(len(info[12].split(','))):
        onthr[x] = int(info[12].split(',')[x].strip('[').strip(']'))
    diffthr =[0 for x in range(len(info[13].split(',')))]
    for x in range(len(info[13].split(','))):
        diffthr[x] = int(info[13].split(',')[x].strip('[').strip(']'))
    offthr = [0 for x in range(len(info[14].split(',')))]
    for x in range(len(info[14].split(','))):
        offthr[x] = int(info[14].split(',')[x].strip('[').strip(']'))
    if(sensor == 'DAVIS208'):
        refss = [0 for x in range(len(info[15].split(',')))]
        for x in range(len(info[15].split(','))):
            refss[x] = int(info[15].split(',')[x].strip('[').strip(']'))

if(do_ptc):
    base_level = 1000.0 #  1 klux
    frame_number = 300.0
#    recording_time = 5
    start_exp = int(info[16].split(',')[0].strip('[').strip(']'))
    end_exp = int(info[16].split(',')[1].strip('[').strip(']'))
    num_points_exp = int(info[16].split(',')[2].strip('[').strip(']'))
    exposures = np.linspace(start_exp, end_exp, num_points_exp)
    if(info[17] == 'False'):
        useinternaladc = False
    elif(info[17] == 'True'):
        useinternaladc = True
    if(info[18] == 'False'):
        global_shutter = False
    elif(info[18] == 'True'):
        global_shutter = True    
        
if(do_frequency_response):
    start_freq = int(info[19].split(',')[0].strip('[').strip(']'))
    end_freq = int(info[19].split(',')[1].strip('[').strip(']'))
    num_points_freq = int(info[19].split(',')[2].strip('[').strip(']'))
    freq_fr = np.logspace(start_freq, end_freq, num = num_points_freq)
    base_level_fr = [1000.0] # 3 points are fine
    contrast_level_fr = [0.5]
    oscillations_fr = 10.0
    ndfilter_fr = info[20]
    
if(do_latency or do_latency_pixel_with_fiber):
    oscillations = 1000.0
    freq_square = 100.0
    base_level_latency_with_fiber = [1000.0]
    contrast_level = 0.5

if(do_oscillations):
    oscillations = 100.0
    freq_square = 10.0
    #oscillations fine values for PrBp
    prbpvalues = np.linspace(3,255,3)   # davi240c [255,25,3] # dvs128   np.linspace(0,1000,5)  
    oscillations_base_level = [60, 500, 1500, 2500, 3000]	#oscillations       

##############################################################################
# SETUP LIGHT CONDITIONS -- MEASURED --
##############################################################################
saturation_level = 3500 # LED saturates at 3.5 klux
volt_applied =np.array([0.0010,0.0020,0.0030,0.0040,0.0050,0.0060,0.0070,0.0080,0.0090,0.0100,0.0110,0.0120,0.0130,0.0140,0.0150,0.0160,0.0170,0.0180,0.0190,0.0200,0.0400,0.0800,0.1000,0.1200,0.1500,0.1700,0.1800,0.2000,0.2200,0.2500,0.3000,0.4000,0.5000])
lux = np.array([24.0,44.0,65.0,86.0,107.6,129.5,151.3,172.9,194.0,216.7,238.9,260.5,283.8,305.1,328.5,349.8,372.4,394.7,416.1,439.1,869.6,1709.0,2110.0,2488.0,3053.0,3399.0,3581.0,3927.0,4191.0,4455.0,4414.0,4389.0,4455.0])
R1 = 100.0 # variable but fixed to this (NEVER change the board)
R2 = 10000.0 # fixed value
voltage_divider = R2/(R1+R2) #voltage divider DC
volt = volt_applied*voltage_divider
index_linear = np.where(lux < saturation_level)[0]
slope, inter = np.polyfit(volt[index_linear],lux[index_linear],1)
plot_setup_characterization = False
if plot_setup_characterization:
    figure()
    plot(volt,lux, 'o', label='measurements')
    xlabel("volt")
    ylabel("lux")
    plot(volt, volt*slope+inter, 'k-', label='fit linear')
    legend(loc='best')

##############################################################################
# 0 - INIT control tools
# init control class and open communication
##############################################################################
control = caer_communication.caer_communication(host=host_ip)
if(dark_room):
    gpio_cnt = gpio_usb.gpio_usb()
    print gpio_cnt.query(gpio_cnt.fun_gen,"*IDN?")
    gpio_cnt.set_inst(gpio_cnt.k230,"I0M1D0F1X") 
    gpio_cnt.set_inst(gpio_cnt.k230,"I2X") # set current limit to max
    gpio_cnt.set_inst(gpio_cnt.k230,"V"+str(0)) #voltage output
    gpio_cnt.set_inst(gpio_cnt.k230,"F1X") #operate

try:
    os.stat(datadir)
except:
    os.mkdir(datadir) 

def copyFile(src, dest):
    try:
        shutil.copy(src, dest)
    # eg. src and dest are the same file
    except shutil.Error as e:
        print('Error: %s' % e)
    # eg. source or destination doesn't exist
    except IOError as e:
        print('Error: %s' % e.strerror)

##############################################################################
## FIND GOOD PARAMETERS
##############################################################################
if(do_set_bias):
    print "Debugging biases: apply 1klux 0.5 contrast sinewave at 1 Hz"
    control.open_communication_command()    
    if(dark_room):
        gpio_cnt.set_inst(gpio_cnt.k230,"I0M1D0F1X") 
        gpio_cnt.set_inst(gpio_cnt.k230,"I2X") # set current limit to max
    sine_freq = 10.0;
    freq_square = 1.0
    base_level = 1000;
    contrast_level = 0.5
    oscillations = 10000; # 10 minutes
    perc_low = base_level-(contrast_level/2.0)*base_level
    perc_hi = base_level+(contrast_level/2.0)*base_level
    v_hi = (perc_hi - inter) / slope
    v_low = (perc_low - inter) / slope 
    offset = np.mean([v_hi,v_low])
    amplitude = (v_hi - np.mean([v_hi,v_low]) )/0.01 #voltage divider AC
    print("offset is "+str(offset)+ " amplitude " +str(amplitude) + " . ")
    if(dark_room):
        #gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:SIN "+str(sine_freq)+", "+str(amplitude)+",0")
        gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:SIN "+str(freq_square)+", "+str(amplitude)+",0")        
        gpio_cnt.set_inst(gpio_cnt.k230,"V"+str(round(offset,3))) #voltage output
        gpio_cnt.set_inst(gpio_cnt.k230,"F1X") #operate
    control.load_biases(xml_file=bias_file, dvs128xml=dvs128xml)
    control.send_command('put /1/1-'+str(sensor_type)+'/'+str(sensor)+'/dvs/ FilterBackgroundActivity bool false')
    control.simple_test(sensor, dvs_use = dvs_use, oscillations = oscillations, frequency = sine_freq, sensor_type = sensor_type, contrast_level = contrast_level, base_level = base_level)
    # Zero the Function Generator
    if(dark_room):
        gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:DC DEF, DEF, 0")
    control.close_communication_command()        

##############################################################################
## TESTS
##############################################################################
# 1 - Photon Transfer Curve - data
# setup is in conditions -> Homegeneous light source (integrating sphere, need to measure the luminosity)
if do_ptc:
    print "\n"
    print "we are doing ptc measurements, please put homogeneous light source (integrating sphere)."
    raw_input("Press Enter to continue...")
    control.open_communication_command()
    if(dark_room):
        # Zero the Function Generator
        gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:DC DEF, DEF, 0")
        # Set the K230 to the chosen luminosity
        gpio_cnt.set_inst(gpio_cnt.k230,"I0M1D0F1X") 
        gpio_cnt.set_inst(gpio_cnt.k230,"I2X") # set current limit to max
    v_base_level = (base_level - inter) / slope
    if(dark_room):
        gpio_cnt.set_inst(gpio_cnt.k230,"V"+str(v_base_level)) #voltage output
        gpio_cnt.set_inst(gpio_cnt.k230,"F1X") #operate
    if(useinternaladc):
        ADCtype = "_ADCint"
    else:
        ADCtype = "_ADCext"
    folder = datadir + '/'+ sensor + ADCtype + '_ptc_' + str(format(base_level,'.0f')) + 'lux_' + current_date
    setting_dir = folder + str("/settings/")
    if(not os.path.exists(setting_dir)):
        os.makedirs(setting_dir)
    control.load_biases(xml_file=bias_file, dvs128xml=dvs128xml)
    copyFile(bias_file, setting_dir+str("biases_ptc_all_exposures.xml") )
    control.get_data_ptc(sensor, folder = folder, frame_number = frame_number, exposures=exposures, global_shutter=global_shutter, sensor_type = sensor_type, useinternaladc = useinternaladc )
    control.close_communication_command()    
    print "Data saved in " +  folder     

# 2 - Contrast sensitivity - data
# setup is in conditions -> Homegeneous light source (integrating sphere, need to measure the luminosity)
if do_contrast_sensitivity:
    control.open_communication_command()
    folder = datadir + '/'+ sensor + '_contrast_sensitivity_' +  current_date
    setting_dir = folder + str("/settings/")
    if(not os.path.exists(setting_dir)):
        os.makedirs(setting_dir)
    copyFile(bias_file, setting_dir+str("biases_contrast_sensitivity.xml") )
    control.load_biases(xml_file=bias_file, dvs128xml=dvs128xml)
    control.send_command('put /1/1-'+str(sensor_type)+'/'+str(sensor)+'/dvs/ FilterBackgroundActivity bool false')
    print "we are doing contrast sentivity measurements, please put homogeneous light source (integrating sphere)."
    if(dark_room):
        gpio_cnt.set_inst(gpio_cnt.k230,"I0M1D0F1X") 
        gpio_cnt.set_inst(gpio_cnt.k230,"I2X") # set current limit to max
    for this_base in range(len(contrast_base_levels)):
        print("Base level: "+str(contrast_base_levels[this_base]))
        for this_contrast in range(len(contrast_level)):
            print("Contrast level: "+str(contrast_level[this_contrast]))
            perc_low = contrast_base_levels[this_base]-(contrast_level[this_contrast]/2.0)*contrast_base_levels[this_base]
            perc_hi = contrast_base_levels[this_base]+(contrast_level[this_contrast]/2.0)*contrast_base_levels[this_base]
            v_hi = (perc_hi - inter) / slope
            v_low = (perc_low - inter) / slope 
            offset = np.mean([v_hi,v_low])
            amplitude = (v_hi - np.mean([v_hi,v_low]) )/0.01 #voltage divider AC
            print("offset is "+str(offset)+ " amplitude " +str(amplitude) + " . ")
            if(dark_room):
                gpio_cnt.set_inst(gpio_cnt.fun_gen,"OUTPut:SYNC ON") # enable sync
                #gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:SIN "+str(sine_freq)+", "+str(amplitude)+",0")
                gpio_cnt.set_inst(gpio_cnt.k230,"V"+str(round(offset,3))) #voltage output
                gpio_cnt.set_inst(gpio_cnt.k230,"F1X") #operate
            #raise Exception
            for this_bias_index in range(len(onthr)):
                print("Bias combination: "+str(this_bias_index))
                #set biases
                #put /1/1-DAVISFX3/bias/DiffBn/ coarseValue byte  4
                #put /1/1-DAVISFX3/bias/DiffBn/ fineValue short 120
                #put /1/1-DAVISFX3/bias/OffBn/ fineValue short 6
                #put /1/1-DAVISFX3/bias/OnBn/ fineValue short 255
                #control.load_biases(xml_file=bias_file, dvs128xml=dvs128xml)
                print "on finevalue " + str(onthr[this_bias_index]) 
                print "diff finevalue" + str(diffthr[this_bias_index]) 
                print "off finevalue" + str(offthr[this_bias_index]) 
                
                control.send_command('put /1/1-'+str(sensor_type)+'/'+str(sensor)+'/bias/OnBn/ fineValue short '+str(onthr[this_bias_index]))
                control.send_command('put /1/1-'+str(sensor_type)+'/'+str(sensor)+'/bias/DiffBn/ fineValue short '+str(diffthr[this_bias_index]))
                control.send_command('put /1/1-'+str(sensor_type)+'/'+str(sensor)+'/bias/OffBn/ fineValue short '+str(offthr[this_bias_index]))
                if (sensor == 'DAVIS208'):
                    #for this_refss in range(len(refss)):
                    if(dark_room):
                        gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:SIN "+str(sine_freq)+", "+str(amplitude)+",0") #enable sine wave
                    print"refss finevalue" + str(refss[this_bias_index])
                    control.send_command('put /1/1-'+str(sensor_type)+'/'+str(sensor)+'/bias/RefSSBn/ fineValue short '+str(refss[this_bias_index]))
                    control.get_data_contrast_sensitivity(sensor, folder = folder, oscillations = oscillations, frequency = sine_freq, sensor_type = sensor_type, contrast_level = contrast_level[this_contrast], base_level = contrast_base_levels[this_base], onthr = onthr[this_bias_index], diffthr = diffthr[this_bias_index], offthr =offthr[this_bias_index], refss = refss[this_bias_index], sinewave = True)
                    if(dark_room):                    
                        gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:DC DEF, DEF, 0") # turn off sine wave                    
                    control.get_data_contrast_sensitivity(sensor, folder = folder, oscillations = oscillations, frequency = sine_freq, sensor_type = sensor_type, contrast_level = contrast_level[this_contrast], base_level = contrast_base_levels[this_base], onthr = onthr[this_bias_index], diffthr = diffthr[this_bias_index], offthr =offthr[this_bias_index], refss = refss[this_bias_index], sinewave = False)
                else:
                    if(dark_room):
                        gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:SIN "+str(sine_freq)+", "+str(amplitude)+",0") #enable sine wave
                    control.get_data_contrast_sensitivity(sensor, folder = folder, oscillations = oscillations, frequency = sine_freq, sensor_type = sensor_type, contrast_level = contrast_level[this_contrast], base_level = contrast_base_levels[this_base], onthr = onthr[this_bias_index], diffthr = diffthr[this_bias_index], offthr =offthr[this_bias_index], refss = 0, sinewave = True)
                    if(dark_room):                    
                        gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:DC DEF, DEF, 0") # turn off sine wave
                    control.get_data_contrast_sensitivity(sensor, folder = folder, oscillations = oscillations, frequency = sine_freq, sensor_type = sensor_type, contrast_level = contrast_level[this_contrast], base_level = contrast_base_levels[this_base], onthr = onthr[this_bias_index], diffthr = diffthr[this_bias_index], offthr =offthr[this_bias_index], refss = 0, sinewave = False)
                    
    # Zero the Function Generator
    if(dark_room):
        gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:DC DEF, DEF, 0")
    control.close_communication_command()        

# 3 - Frequency response - data
# setup is in conditions -> Homegeneous light source (integrating sphere, need to measure the luminosity)
if do_frequency_response:
    control.open_communication_command()
    folder = datadir + '/'+ sensor + '_frequency_response_' +  current_date
    setting_dir = folder + str("/settings/")
    if(not os.path.exists(setting_dir)):
        os.makedirs(setting_dir)
    copyFile(bias_file, setting_dir+str("biases_frequency_response.xml") )
    control.load_biases(xml_file=bias_file, dvs128xml=dvs128xml)
    print "we are doing frequency response measurements, please put big led setup."
    if(dark_room):
        gpio_cnt.set_inst(gpio_cnt.k230,"I0M1D0F1X") 
        gpio_cnt.set_inst(gpio_cnt.k230,"I2X") # set current limit to max
    for this_base in range(len(base_level_fr)):
        print("Base level: "+str(base_level_fr[this_base]))
        for this_contrast in range(len(contrast_level_fr)):
            print("Contrast level: "+str(contrast_level_fr[this_contrast]))            
            perc_low = base_level_fr[this_base]-(contrast_level_fr[this_contrast]/2.0)*base_level_fr[this_base]
            perc_hi = base_level_fr[this_base]+(contrast_level_fr[this_contrast]/2.0)*base_level_fr[this_base]
            v_hi = (perc_hi - inter) / slope
            v_low = (perc_low - inter) / slope 
            offset = np.mean([v_hi,v_low])
            amplitude = (v_hi - np.mean([v_hi,v_low]) )/0.01 #voltage divider AC
            print("offset is "+str(offset)+ " amplitude " +str(amplitude) + " . ")
            for this_freq in range(len(freq_fr)):
                print("Frequency: "+str(freq_fr[this_freq]))+" Hz"
                if(dark_room):
                    gpio_cnt.set_inst(gpio_cnt.fun_gen,"OUTPut:SYNC ON") # enable sync
#                    gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:SIN "+str(freq_fr[this_freq])+", "+str(amplitude)+",0")
                    gpio_cnt.set_inst(gpio_cnt.k230,"V"+str(round(offset,3))) #voltage output
                    gpio_cnt.set_inst(gpio_cnt.k230,"F1X") #operate
                control.load_biases(xml_file=bias_file, dvs128xml=dvs128xml)
                sine_freq = freq_fr[this_freq]
                if (not sensor == "DAVIS240C"):
                    control.send_command('put /1/1-'+str(sensor_type)+'/'+str(sensor)+'/dvs/ FilterBackgroundActivity bool false')
                if(dark_room):
                    gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:SIN "+str(freq_fr[this_freq])+", "+str(amplitude)+",0") #enable sine wave
                control.get_data_frequency_response(sensor, folder = folder, oscillations = oscillations_fr, frequency = freq_fr[this_freq], sensor_type = sensor_type, contrast_level = contrast_level_fr[this_contrast], base_level = base_level_fr[this_base], ndfilter = ndfilter_fr, sinewave = True)
                if(dark_room):                    
                    gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:DC DEF, DEF, 0") # turn off sine wave
                control.get_data_frequency_response(sensor, folder = folder, oscillations = oscillations_fr, frequency = freq_fr[this_freq], sensor_type = sensor_type, contrast_level = contrast_level_fr[this_contrast], base_level = base_level_fr[this_base], ndfilter = ndfilter_fr, sinewave = False)
    # Zero the Function Generator
    if(dark_room):
        gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:DC DEF, DEF, 0")
    control.close_communication_command()
    print "Data saved in " +  folder
        
# 4 - Oscillations - data
# setup is in conditions -> Homegeneous light source (integrating sphere, need to measure the luminosity)
if do_oscillations:
    print "\n"
    print "we are doing oscillations measurements. ..\n \
	WARNING : remember to check that CAER has network streaming enable sends both spiking events and special events ..\n \
        1_ Check that the setup is illuminated correctly..\n \
        2_ Connect the synch cable from the output of the function generator to the synch input on the DVS board..\n \
        3_ Check the options in run_all test.. WARNING: remember to specify the filter type that you are using"
    raw_input("Press Enter to continue...")

    filter_type = 2.0
    control.open_communication_command()
    control.load_biases(xml_file=bias_file, dvs128xml=dvs128xml)    
    folder = datadir + '/'+ sensor + '_oscillations_' +  current_date
    setting_dir = folder + str("/settings/")
    if(not os.path.exists(setting_dir)):
        os.makedirs(setting_dir)
    num_measurements = len(oscillations_base_level) 
    #base_level_v = 1.5
    #base_level = [base_level_v+step_level*i for i in range(num_measurements)]
    recording_time = (1.0/freq_square)*num_oscillations # number of complete oscillations
    if(dark_room):
        gpio_cnt.set_inst(gpio_cnt.k230,"I0M1D0F1X") 
        gpio_cnt.set_inst(gpio_cnt.k230,"I2X") # set current limit to max
    copyFile(bias_file, setting_dir+str("biases_oscillations_all_exposures_prchanged.xml") )
    for this_bias in range(len(prbpvalues)):
        for i in range(num_measurements):
            print("Base level: "+str(oscillations_base_level[i]))
            perc_low = oscillations_base_level[i]-(contrast_level/2.0)*oscillations_base_level[i]
            perc_hi = oscillations_base_level[i]+(contrast_level/2.0)*oscillations_base_level[i]
            v_hi = (perc_hi - inter) / slope
            v_low = (perc_low - inter) / slope 
            offset = np.mean([v_hi,v_low])
            amplitude = (v_hi - np.mean([v_hi,v_low]) )/0.01 #voltage divider AC
            print("offset is "+str(offset)+ " amplitude " +str(amplitude) + " . ")
            if(dark_room):
                gpio_cnt.set_inst(gpio_cnt.fun_gen,"OUTPut:SYNC ON") # enable sync
                gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:SQUARE "+str(freq_square)+", "+str(amplitude)+",0")
                gpio_cnt.set_inst(gpio_cnt.k230,"V"+str(round(offset,3))) #voltage output
                gpio_cnt.set_inst(gpio_cnt.k230,"F1X") #operate
            if(dvs128xml):
                control.send_command('put /1/1-DVS128/'+str(sensor)+'/bias/ pr int '+str(int(prbpvalues[this_bias])))
            else:
                control.send_command('put /1/1-DAVISFX2/'+str(sensor)+'/bias/RefrBp/ fineValue short '+str(prbpvalues[this_bias]))
            control.get_data_oscillations(sensor, folder = folder, recording_time = recording_time, num_measurement = i, lux=oscillations_base_level[i], filter_type=filter_type, sensor_type = sensor_type, prbias = prbpvalues[this_bias], dvs128xml = dvs128xml)
    control.close_communication_command()    
    print "Data saved in " +  folder

# 5 - Latency small led on board with all colored leds - data
# setup is in conditions -> flashing LED
if do_latency_pixel_with_fiber:
    print "\n"
    print "we are doing latency measurements. Connect the synch cable from the output of the function generator to the synch input on the DVS board."
    raw_input("Press Enter to continue...")

    filter_type = 2.0
    control.open_communication_command()
    control.load_biases(xml_file=bias_file, dvs128xml=dvs128xml)    
    folder = datadir + '/'+ sensor + '_oscillations_' +  current_date
    setting_dir = folder + str("/settings/")

    if(not os.path.exists(setting_dir)):
        os.makedirs(setting_dir)

    num_measurements = len(base_level_latency_with_fiber) 
    #base_level_v = 1.5
    #base_level = [base_level_v+step_level*i for i in range(num_measurements)]
    recording_time = (1.0/freq_square)*oscillations # number of complete oscillations
    if(dark_room):
        gpio_cnt.set_inst(gpio_cnt.k230,"I0M1D0F1X") 
        gpio_cnt.set_inst(gpio_cnt.k230,"I2X") # set current limit to max
    if(not os.path.exists(setting_dir)):
        os.makedirs(setting_dir)
    copyFile(bias_file, setting_dir+str("biases_latencies_all_exposures.xml") )
    for i in range(num_measurements):
        print("Base level: "+str(base_level_latency_with_fiber[i]))
        perc_low = base_level_latency_with_fiber[i]-(contrast_level/2.0)*base_level_latency_with_fiber[i]
        perc_hi = base_level_latency_with_fiber[i]+(contrast_level/2.0)*base_level_latency_with_fiber[i]
        v_hi = (perc_hi - inter) / slope
        v_low = (perc_low - inter) / slope 
        offset = np.mean([v_hi,v_low])
        amplitude = (v_hi - np.mean([v_hi,v_low]) )/0.01 #voltage divider AC
        print("offset is "+str(offset)+ " amplitude " +str(amplitude) + " . ")
        if(dark_room):
            gpio_cnt.set_inst(gpio_cnt.fun_gen,"OUTPut:SYNC ON") # enable sync
            gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:SQUARE "+str(freq_square)+", "+str(amplitude[0])+",0")
            gpio_cnt.set_inst(gpio_cnt.k230,"V"+str(round(offset,3))) #voltage output
            gpio_cnt.set_inst(gpio_cnt.k230,"F1X") #operate
        control.load_biases(xml_file=bias_file, dvs128xml=dvs128xml)
        control.send_command('put /1/1-'+str(sensor_type)+'/'+str(sensor)+'/dvs/ FilterBackgroundActivity bool false')
        copyFile(bias_file, setting_dir+str("biases_meas_num_"+str(i)+".xml") )
        time.sleep(3)
        control.get_data_latency(sensor, folder = folder, recording_time = recording_time, num_measurement = i, lux=lux[i], filter_type=filter_type, sensor_type = sensor_type)
    control.close_communication_command()    
    print "Data saved in " +  folder
 
# 6 - Latency fiber pointing at the sensor - data
# setup is in conditions -> flashing LED
if do_latency:
    print "\n"
    print "we are doing latency measurements. Connect the synch cable from the output of the function generator to the synch input on the DVS board."
    raw_input("Press Enter to continue...")

    filter_type = 0.0
    control.open_communication_command()
    control.load_biases(xml_file=bias_file, dvs128xml=dvs128xml)    
    folder = datadir + '/'+ sensor + '_latency_' +  current_date
    setting_dir = folder + str("/settings/")

    if(not os.path.exists(setting_dir)):
        os.makedirs(setting_dir)

    num_measurements = len(base_level_latency_with_fiber) 
    #base_level_v = 1.5
    #base_level = [base_level_v+step_level*i for i in range(num_measurements)]
    recording_time = (1.0/freq_square)*oscillations # number of complete oscillations
    if(dark_room):
        gpio_cnt.set_inst(gpio_cnt.k230,"I0M1D0F1X") 
        gpio_cnt.set_inst(gpio_cnt.k230,"I2X") # set current limit to max
    if(not os.path.exists(setting_dir)):
        os.makedirs(setting_dir)
    copyFile(bias_file, setting_dir+str("biases_latencies_all_exposures.xml") )
    for i in range(num_measurements):
        print("Base level: "+str(base_level_latency_with_fiber[i]))
        perc_low = base_level_latency_with_fiber[i]-(contrast_level/2.0)*base_level_latency_with_fiber[i]
        perc_hi = base_level_latency_with_fiber[i]+(contrast_level/2.0)*base_level_latency_with_fiber[i]
        v_hi = (perc_hi - inter) / slope
        v_low = (perc_low - inter) / slope 
        offset = np.mean([v_hi,v_low])
        amplitude = (v_hi - np.mean([v_hi,v_low]) )/0.01 #voltage divider AC
        print("offset is "+str(offset)+ " amplitude " +str(amplitude) + " . ")
        if(dark_room):
            gpio_cnt.set_inst(gpio_cnt.fun_gen,"OUTPut:SYNC ON") # enable sync
            gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:SQUARE "+str(freq_square)+", "+str(amplitude)+",0")
            gpio_cnt.set_inst(gpio_cnt.k230,"V"+str(round(offset,3))) #voltage output
            gpio_cnt.set_inst(gpio_cnt.k230,"F1X") #operate
        control.load_biases(xml_file=bias_file, dvs128xml=dvs128xml)
        control.send_command('put /1/1-'+str(sensor_type)+'/'+str(sensor)+'/dvs/ FilterBackgroundActivity bool false')
        copyFile(bias_file, setting_dir+str("biases_meas_num_"+str(i)+".xml") )
        time.sleep(3)
        control.get_data_latency(sensor, folder = folder, recording_time = recording_time, num_measurement = i, lux=lux[i], filter_type=filter_type, sensor_type = sensor_type)
    control.close_communication_command()    
    print "Data saved in " +  folder

## switch off everything (hp function gen etc..)
if(dark_room):
    gpio_cnt.set_inst(gpio_cnt.fun_gen,"APPL:DC DEF, DEF, 0")
    gpio_cnt.set_inst(gpio_cnt.k230,"I0M1D0F1X") 
    gpio_cnt.set_inst(gpio_cnt.k230,"I2X") # set current limit to max
    gpio_cnt.set_inst(gpio_cnt.k230,"V"+str(0)) #voltage output
    gpio_cnt.set_inst(gpio_cnt.k230,"F1X") #operate