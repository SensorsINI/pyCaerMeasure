import sys

sys.path.append('utils/')
import load_files

sys.path.append('analysis/')
import DVS_contrast_sensitivity
# import DVS_latency
import DVS_oscillations
import DVS_frequency_response
import APS_photon_transfer_curve
import matplotlib as plt
from pylab import *
import numpy as np
import os
import winsound

# winsound.Beep(300,1000)
plt.close("all")
ioff()
##############################################################################
# ANALYSIS
##############################################################################
do_ptc = False
do_frequency_response = False
do_latency_pixel = False
do_contrast_sensitivity = False
do_oscillations = True

################### 
# GET CHIP INFO
###################

# PTC DARK LONG
# directory_meas = ["Z:/Characterizations/Measurements_final/DAVIS208/PTC/DAVIS208_ADCint_ptc_07_06_16-15_59_39_dark_long_coveredleds_shortned/",
#                  "Z:/Characterizations/Measurements_final/QE/QE_DAVIS240C_30_06_16-17_52_22/DAVIS240C_ADCext_ptc_dark_1000lux_05_07_16-16_26_10/"]

# PTC DARK SHORT
# directory_meas = ["Z:/Characterizations/Measurements_final/DAVIS208/PTC/Measurements_07_06_2016/DARK/DAVIS208_ADCint_ptc_07_06_16-15_41_37_dark_short/",
#                  "Z:/Characterizations/Measurements/DAVIS240C_ADCext_ptc_dark_22_06_16-18_23_22/"]

##PTC LIGHT
# directory_meas = ["Z:/Characterizations/Measurements_final/DAVIS208/PTC/Measurements_07_06_2016/LIGHT/DAVIS208_ADCint_ptc_07_06_16-15_29_42_light/",
#                  "Z:/Characterizations/Measurements_final/DAVIS240C/PTC/DAVIS240C_ADCext_ptc_1000lux_05_07_16-09_11_29light/"]

# Contrast
directory_meas = ['Z:/Characterizations/Measurements_final/346BSI/latency/DAVIS346C_latency_irc_nd2_05_08_16-18_28_01/']

# directory_meas = "Z:/Characterizations/Measurements_final/DAVIS208/PTC/Measurements_07_06_2016/DARK/DAVIS208_ADCint_ptc_07_06_16-15_51_10_dark_short_coveredleds/"
# directory_meas = "Z:/Characterizations/Measurements_final/DAVIS208/PTC/Measurements_07_06_2016/DARK/DAVIS208_ADCint_ptc_07_06_16-15_41_37_dark_short/"
# directory_meas = "Z:/Characterizations/Measurements_final/DAVIS208/PTC/Measurements_07_06_2016/LIGHT/DAVIS208_ADCint_ptc_07_06_16-15_17_01_light/"
# directory_meas = "Z:/Characterizations/Measurements_final/DAVIS208/PTC/Measurements_07_06_2016/LIGHT/DAVIS208_ADCint_ptc_07_06_16-15_29_42_light/"
# directory_meas = "Z:/Characterizations/Measurements_final/DAVIS208/PTC/Measurements_07_06_2016/LIGHT/DAVIS208_ADCint_ptc_08_06_16-16_16_58_light/"

# directory_meas= "Z:/Characterizations/Measurements_final/346F/chip1/DAVIS346B_ADCint_ptc_20_06_16-15_37_22_light/"
# directory_meas= "Z:/Characterizations/Measurements_final/346F/chip1/DAVIS346B_ADCint_ptc_20_06_16-16_10_43_dark_short/"
# directory_meas= "Z:/Characterizations/Measurements_final/346F/chip1/DAVIS346B_ADCint_ptc_20_06_16-16_26_43_dark_long/"

camera_file = ['cameras/davis346_parameters.txt']
# camera_file = 'cameras/davis346_parameters.txt'

for index_chip in range(len(directory_meas)):
    info = np.genfromtxt(camera_file[index_chip], dtype='str')
    sensor = info[0]
    sensor_type = info[1]
    bias_file = info[2]
    if (info[3] == 'False'):
        dvs128xml = False
    elif (info[3] == 'True'):
        dvs128xml == True
    host_ip = info[4]
    camera_dim = [int(info[5].split(',')[0].strip('[').strip(']')), int(info[5].split(',')[1].strip('[').strip(']'))]
    pixel_sel = [int(info[6].split(',')[0].strip('[').strip(']')), int(info[6].split(',')[1].strip('[').strip(']'))]
    ADC_range_int = float(info[7])
    ADC_range_ext = float(info[8])
    ADC_values = float(info[9])
    frame_x_divisions = [[0 for x in range(2)] for x in range(len(info[10].split(',')) / 2)]
    for x in range(0, len(info[10].split(',')), 2):
        frame_x_divisions[x / 2][0] = int(info[10].split(',')[x].strip('[').strip(']'))
        frame_x_divisions[x / 2][1] = int(info[10].split(',')[x + 1].strip('[').strip(']'))
    frame_y_divisions = [[0 for y in range(2)] for y in range(len(info[11].split(',')) / 2)]
    for y in range(0, len(info[11].split(',')), 2):
        frame_y_divisions[y / 2][0] = int(info[11].split(',')[y].strip('[').strip(']'))
        frame_y_divisions[y / 2][1] = int(info[11].split(',')[y + 1].strip('[').strip(']'))

    ################### 
    # PARAMETERS
    ###################
    if (do_contrast_sensitivity):
        sine_freq = 1.0
        num_oscillations = 10.0
        single_pixels_analysis = True
        rmse_reconstruction = False

    if (do_frequency_response):
        num_oscillations = 10.0
        size_led = 3.0

    ################### 
    # END PARAMETERS
    ###################

    if do_contrast_sensitivity:
        #######################
        # CONTRAST SENSITIVITY
        #######################
        cs_dir = directory_meas[index_chip]
        figure_dir = cs_dir + 'figures/'
        if (not os.path.exists(figure_dir)):
            os.makedirs(figure_dir)
        # select test pixels areas only two are active
        aedat = DVS_contrast_sensitivity.DVS_contrast_sensitivity()
        contrast_level, base_level, on_level, diff_level, off_level, refss_level, contrast_sensitivity_off_average_array, \
        contrast_sensitivity_on_average_array, contrast_sensitivity_off_median_array, contrast_sensitivity_on_median_array, \
        err_on_percent_array, err_off_percent_array = aedat.cs_analysis(sensor, cs_dir, \
                                                                        figure_dir, frame_y_divisions,
                                                                        frame_x_divisions, sine_freq=sine_freq,
                                                                        num_oscillations=num_oscillations, \
                                                                        single_pixels_analysis=single_pixels_analysis,
                                                                        rmse_reconstruction=rmse_reconstruction,
                                                                        camera_dim=camera_dim)

    if do_frequency_response:
        #####################
        # FREQUENCY RESPONSE
        #####################
        fr_dir = directory_meas[index_chip]
        figure_dir = fr_dir + 'figures/'
        if (not os.path.exists(figure_dir)):
            os.makedirs(figure_dir)
        # select test pixels areas only two are active
        aedat = DVS_frequency_response.DVS_frequency_response()
        contrast_level, base_level, frequency, contrast_sensitivity_off_average_array, \
        off_event_count_median_per_pixel, on_event_count_median_per_pixel, \
        off_event_count_average_per_pixel, on_event_count_average_per_pixel, \
        contrast_sensitivity_on_average_array, contrast_sensitivity_off_median_array, \
        contrast_sensitivity_on_median_array, err_on_percent_array, err_off_percent_array = \
            aedat.fr_analysis(fr_dir, figure_dir, frame_y_divisions=frame_y_divisions, \
                              frame_x_divisions=frame_x_divisions, num_oscillations=num_oscillations, \
                              camera_dim=camera_dim, size_led=size_led)

    if do_ptc:
        #######################
        # PHOTON TRANSFER CURVE
        #######################
        ## Photon transfer curve and sensitivity plot
        # select test pixels areas
        # note that x and y might be swapped inside the ptc_analysis function
        aedat = APS_photon_transfer_curve.APS_photon_transfer_curve()
        ptc_dir = directory_meas[index_chip]
        print str(sensor)
        if ('_ADCint' in ptc_dir):
            ADC_range = ADC_range_int
        else:
            ADC_range = ADC_range_ext
        if (ptc_dir.lower().find('dark') > 0):
            i_pd_es = aedat.ptc_analysis(sensor, ptc_dir, frame_y_divisions, frame_x_divisions, ADC_range, ADC_values,
                                         index_chip)
        else:
            #i_pd_vs, Gain_uVe_lin = aedat.ptc_analysis(sensor, ptc_dir, frame_y_divisions, frame_x_divisions, ADC_range,
            #                                           ADC_values, index_chip)
            i_pd_vs, Gain_uVe_lin = aedat.ptc_analysis(sensor, ptc_dir, frame_y_divisions, frame_x_divisions, ADC_range,
                                                       ADC_values)

    if do_oscillations:
        #######################
        # LATENCY
        #######################
        # latency_pixel_dir = 'measurements/Measurements_final/DAVIS240C_latency_25_11_15-16_35_03_FAST_0/'
        latency_pixel_dir = directory_meas[index_chip]
        figure_dir = latency_pixel_dir + '/figures/'
        if (not os.path.exists(figure_dir)):
            os.makedirs(figure_dir)
        # select test pixels areas only two are active
        aedat = DVS_oscillations.DVS_oscillations()
        all_lux, all_prvalues, all_originals, all_folded, all_pol, all_ts, all_final_index = aedat.oscillations_latency_analysis(
            sensor, latency_pixel_dir, figure_dir, camera_dim=camera_dim, size_led=8, confidence_level=0.95, do_plot=True,
            file_type="cAER", edges=2, dvs128xml=False, pixel_sel=False, latency_only=True)

plt.close("all")
