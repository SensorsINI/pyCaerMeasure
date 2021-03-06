# ############################################################
# python class that deals with cAER aedat3 file format
# and calculates PHOTON TRANSFER CURVE of APS
# author  Federico Corradi - federico.corradi@inilabs.com
# author  Diederik Paul Moeys - diederikmoeys@live.com
# 
# 25th Mmay 2016 - Tested by ChengHan
#
# ############################################################
from __future__ import division
import os
import struct
import threading
import sys
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
import string
from pylab import *
import scipy.stats as st
import math
sys.path.append('utils/')
import load_files
#import winsound

class APS_photon_transfer_curve:
    def ptc_analysis(self, sensor, ptc_dir, frame_y_divisions, frame_x_divisions, ADC_range, ADC_values):
        '''
            Photon transfer curve and sensitivity plot
         
        '''    
        figure_dir = ptc_dir+'figures/'
        if(not os.path.exists(figure_dir)):
            os.makedirs(figure_dir)
        #pixel_area = (18e-6*18e-6)
        exposure_time_scale = 10e-6
        directory = ptc_dir
        files_in_dir = os.listdir(directory)
        files_in_dir.sort()
        u_y_tot = np.zeros([len(files_in_dir),len(frame_y_divisions),len(frame_x_divisions)])+1*-1
        sigma_tot = np.zeros([len(files_in_dir),len(frame_y_divisions),len(frame_x_divisions)])+1*-1
        exposures = np.zeros([len(files_in_dir),len(frame_y_divisions),len(frame_x_divisions)])
        FPN_all = np.zeros([len(files_in_dir),len(frame_y_divisions),len(frame_x_divisions)])+1*-1
        mean_y_FPN_all = np.zeros([len(files_in_dir),len(frame_y_divisions),len(frame_x_divisions)])+1*-1
        mean_x_FPN_all = np.zeros([len(files_in_dir),len(frame_y_divisions),len(frame_x_divisions)])+1*-1
        FPN_in_x_all = np.zeros([len(files_in_dir),len(frame_y_divisions),len(frame_x_divisions)])+1*-1
        FPN_in_y_all = np.zeros([len(files_in_dir),len(frame_y_divisions),len(frame_x_divisions)])+1*-1
        FPN_50 = np.zeros([len(frame_y_divisions),len(frame_x_divisions)])
        mean_y_FPN_50 = np.zeros([len(frame_y_divisions),len(frame_x_divisions)])
        mean_x_FPN_50 = np.zeros([len(frame_y_divisions),len(frame_x_divisions)])
        FPN_in_x_50 = np.zeros([len(frame_y_divisions),len(frame_x_divisions)])
        FPN_in_y_50 = np.zeros([len(frame_y_divisions),len(frame_x_divisions)])
        u_y_tot_50perc = np.zeros([len(frame_y_divisions),len(frame_x_divisions)])
        Gain_uVe_log = np.zeros([len(frame_y_divisions),len(frame_x_divisions)])
        Gain_uVe_lin = np.zeros([len(frame_y_divisions),len(frame_x_divisions)])
        i_pd_es = np.zeros([len(frame_y_divisions),len(frame_x_divisions)])
        i_pd_vs = np.zeros([len(frame_y_divisions),len(frame_x_divisions)])
        all_frames = []
        done = False

        for this_file in range(len(files_in_dir)):
            print "####################################"
            print("processing gray values from file ", str(files_in_dir[this_file]))
            while( not files_in_dir[this_file].endswith(".aedat")):
                print("not a valid data file ", str(files_in_dir[this_file]))
                this_file  = this_file + 1
                if(this_file == len(files_in_dir)):
                    done = True
                    break
            if(done == True):
                break
            shutter_type, exp = files_in_dir[this_file].strip(".aedat").strip("ptc_").strip("shutter_").split("_") # in us
            exp = float(exp)
            loader = load_files.load_files()
            [frame, xaddr, yaddr, pol, ts, sp_type, sp_t] = loader.load_file(directory+files_in_dir[this_file])

            #rescale frame to their values and divide the test pixels areas
            #for this_frame in range(len(frame)):
            for this_div_x in range(len(frame_x_divisions)) :
                for this_div_y in range(len(frame_y_divisions)): 
                    if sensor == 'DAVISHet640':           
                        frame_areas = [frame[this_frame][frame_y_divisions[this_div_y][0]:frame_y_divisions[this_div_y][1]:2, frame_x_divisions[this_div_x][0]:frame_x_divisions[this_div_x][1]:2] for this_frame in range(len(frame))]
                    else:
                        frame_areas = [frame[this_frame][frame_y_divisions[this_div_y][0]:frame_y_divisions[this_div_y][1], frame_x_divisions[this_div_x][0]:frame_x_divisions[this_div_x][1]] for this_frame in range(len(frame))]
                    all_frames.append(frame_areas)
                    frame_areas = np.right_shift(frame_areas,6)
                    n_frames, ydim, xdim = np.shape(frame_areas)   
                    #avr_all_frames = []
                    #for this_frame in range(n_frames):
                    #    avr_all_frames.append(np.mean(frame_areas[this_frame]))
                    #avr_all_frames = np.array(avr_all_frames)       
                    #u_y = (1.0/(n_frames*ydim*xdim)) * np.sum(np.sum(frame_areas,0))  # 
                    ydim_f , xdim_f = np.shape(frame_areas[0])
                    temporal_mean = np.zeros([ydim_f, xdim_f])
                    spatio_mean = np.zeros([n_frames])
                    temporal_variance = np.zeros([ydim_f, xdim_f])
                    temporal_variance_EMVA = 0
                    factor = (1.0/(2.0*float(xdim_f*ydim_f)))
                    for this_frame in range(n_frames):
                        spatio_mean[this_frame]=np.mean(np.mean(frame_areas[this_frame,:,:],0),0)
                    #raise Exception
                    for tx in range(xdim_f):
                        for ty in range(ydim_f):
                            temporal_mean[ty,tx] = np.mean(frame_areas[:,ty,tx])
                            #temporal_variance[ty,tx] =  np.sum((frame_areas[:,ty,tx]-temporal_mean[ty,tx])**2)/n_frames
                            temporal_variance_EMVA = temporal_variance_EMVA + ((frame_areas[20,ty,tx]-spatio_mean[20])- (frame_areas[21,ty,tx]-spatio_mean[21]))**2.0
                    temporal_variance_EMVA = factor*temporal_variance_EMVA
                    #sigma_y = np.mean(temporal_variance)
                    sigma_y = temporal_variance_EMVA
                    spatio_temporal_mean = np.mean(np.mean(temporal_mean,0),0)
                    spatio_var_temporal_mean = 0.0
                    y_var_temporal_mean = np.zeros([xdim_f])
                    x_var_temporal_mean = np.zeros([ydim_f])
                    y_temporal_mean = np.mean(temporal_mean,0)
                    x_temporal_mean = np.mean(temporal_mean,1)
                    spatio_var_y_temporal_mean = 0.0
                    spatio_var_x_temporal_mean = 0.0
                    
                    # mean X and Y FPN
                    for tx in range(xdim_f):
                        #spatio_temporal_y_mean = np.mean(np.mean(temporal_mean[tx,:]))
                        for ty in range(ydim_f):
                            y_var_temporal_mean[tx] = y_var_temporal_mean[tx] + (temporal_mean[ty,tx] - y_temporal_mean[tx])**2.0
                        y_var_temporal_mean[tx] = y_var_temporal_mean[tx] / ydim_f
                    mean_y_FPN = np.mean((y_var_temporal_mean)**0.5)
                    
                    for ty in range(ydim_f):
                        #raise Exception
                        #spatio_temporal_x_mean = np.mean(np.mean(temporal_mean[:,ty]))
                        for tx in range(xdim_f):
                            x_var_temporal_mean[ty] = x_var_temporal_mean[ty] + (temporal_mean[ty,tx] - x_temporal_mean[ty])**2.0
                        x_var_temporal_mean[ty] = x_var_temporal_mean[ty] / xdim_f
                    mean_x_FPN = np.mean((x_var_temporal_mean)**0.5)
                    
                    # Just ADC contribution
                    for tx in range(xdim_f):
                        spatio_var_y_temporal_mean = spatio_var_y_temporal_mean + (y_temporal_mean[tx] - spatio_temporal_mean)**2.0
                    spatio_var_y_temporal_mean = spatio_var_y_temporal_mean / xdim_f
                    FPN_in_x = spatio_var_y_temporal_mean**0.5

                    for ty in range(ydim_f):
                        spatio_var_x_temporal_mean = spatio_var_x_temporal_mean + (x_temporal_mean[ty] - spatio_temporal_mean)**2.0
                    spatio_var_x_temporal_mean = spatio_var_x_temporal_mean / ydim_f
                    FPN_in_y = spatio_var_x_temporal_mean**0.5
                    
                    # All
                    for tx in range(xdim_f):
                        for ty in range(ydim_f):
                            spatio_var_temporal_mean = spatio_var_temporal_mean + (temporal_mean[ty,tx] - spatio_temporal_mean)**2.0
                    spatio_var_temporal_mean = spatio_var_temporal_mean / (xdim_f * ydim_f)
                    FPN = spatio_var_temporal_mean**0.5
#                    if(ptc_dir.lower().find('debug') >= 0):
                    print "--------------------------------------------"
                    print "X: " + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y])
                    print "FPN: " + str(FPN) + " DN"
                    print "Temporal var: " + str(sigma_y) + " DN"
                    print str(n_frames) + " frames recorded." 
#                    print(str(np.shape(all_frames)) + " all_frames.")
                    u_y_tot[this_file, this_div_y, this_div_x] = spatio_temporal_mean
                    sigma_tot[this_file, this_div_y, this_div_x] = sigma_y
                    exposures[this_file, this_div_y, this_div_x] = exp
                    FPN_all[this_file, this_div_y, this_div_x] = FPN
                    mean_y_FPN_all[this_file, this_div_y, this_div_x] = mean_y_FPN
                    mean_x_FPN_all[this_file, this_div_y, this_div_x] = mean_x_FPN
                    FPN_in_x_all[this_file, this_div_y, this_div_x] = FPN_in_x
                    FPN_in_y_all[this_file, this_div_y, this_div_x] = FPN_in_y
                            
        if(ptc_dir.lower().find('debug') < 0):        
            #just remove entry that corresponds to files that are not measurements
            files_num, y_div, x_div = np.shape(exposures)
            to_remove = len(np.unique(np.where(exposures == 0)[0]))
            exposures_real = exposures[exposures != 0]
            exposures = np.reshape(exposures_real, [files_num-to_remove, y_div, x_div])
            u_y_tot_real = u_y_tot[u_y_tot != -1]
            u_y_tot =  np.reshape(u_y_tot_real, [files_num-to_remove, y_div, x_div])
            sigma_tot_real = sigma_tot[sigma_tot != -1]
            sigma_tot =  np.reshape(sigma_tot_real, [files_num-to_remove, y_div, x_div])
            FPN_all_real = FPN_all[FPN_all != -1]
            FPN_all = np.reshape(FPN_all_real, [files_num-to_remove, y_div, x_div])
            mean_y_FPN_all_real = mean_y_FPN_all[mean_y_FPN_all != -1]
            mean_y_FPN_all = np.reshape(mean_y_FPN_all_real, [files_num-to_remove, y_div, x_div])
            mean_x_FPN_all_real = mean_x_FPN_all[mean_x_FPN_all != -1]
            mean_x_FPN_all = np.reshape(mean_x_FPN_all_real, [files_num-to_remove, y_div, x_div])
            FPN_in_x_all_real = FPN_in_x_all[FPN_in_x_all != -1]
            FPN_in_x_all = np.reshape(FPN_in_x_all_real, [files_num-to_remove, y_div, x_div])
            FPN_in_y_all_real = FPN_in_y_all[FPN_in_y_all != -1]
            FPN_in_y_all = np.reshape(FPN_in_y_all_real, [files_num-to_remove, y_div, x_div])
            
            exposures = exposures[:,0,0]
            #all_frames = np.array(all_frames)
            #plt.figure()
            #plt.title("all frames values")
            #for i in range(len(all_frames)):
            #    this_ff = np.reshape(all_frames[i], len(all_frames[i]))
            #    this_dn_f = np.right_shift(this_ff,6)
            #    plot(this_dn_f) 
            #plt.xlabel("frame number")   
            #plt.legend(loc='best')
            #plt.xlabel('frame number') 
            #plt.ylabel('DN value single pixel') 
            #plt.savefig(figure_dir+"dn_value_single_pixel.pdf",  format='pdf') 
            #plt.savefig(figure_dir+"dn_value_single_pixel.png",  format='png')  
        
            #FPN 50% sat level
            for this_div_x in range(len(frame_x_divisions)) :
                for this_div_y in range(len(frame_y_divisions)):
                    range_u_y_tot = np.max(u_y_tot[:, this_div_y, this_div_x])-np.min(u_y_tot[:, this_div_y, this_div_x])
                    u_y_tot_50perc[this_div_y, this_div_x] = np.min(u_y_tot[:, this_div_y, this_div_x]) + range_u_y_tot/2.0
                    indu_y_tot_50perc = np.where(u_y_tot[:,this_div_y,this_div_x]  >= u_y_tot_50perc[this_div_y, this_div_x])[0][0]
                    FPN_50[this_div_y, this_div_x] = FPN_all[indu_y_tot_50perc,this_div_y,this_div_x]
                    mean_y_FPN_50[this_div_y, this_div_x] = mean_y_FPN_all[indu_y_tot_50perc,this_div_y,this_div_x]
                    mean_x_FPN_50[this_div_y, this_div_x] = mean_x_FPN_all[indu_y_tot_50perc,this_div_y,this_div_x]
                    FPN_in_x_50[this_div_y, this_div_x] = FPN_in_x_all[indu_y_tot_50perc,this_div_y,this_div_x]
                    FPN_in_y_50[this_div_y, this_div_x] = FPN_in_y_all[indu_y_tot_50perc,this_div_y,this_div_x]
                    print "X: " + str(frame_x_divisions[this_div_x]) + ", Y: " + str(frame_y_divisions[this_div_y])
                    print "Saturating DN: " + str(np.max(u_y_tot[:, this_div_y, this_div_x])) + " DN"
                    print "Sarting DN: " + str(np.min(u_y_tot[:, this_div_y, this_div_x])) + " DN"
                    print "50% point: " + str(u_y_tot_50perc[this_div_y, this_div_x]) + " DN"
                    print "FPN at 50% sat level (DN): " + str(FPN_50[this_div_y, this_div_x]) + " DN"
                    print "FPN at 50% sat level (%): " + str(100.0*(FPN_50[this_div_y, this_div_x]/u_y_tot_50perc[this_div_y, this_div_x])) + "%"
                    print "Mean y FPN of every x at 50% sat level (%): " + str(format(100.0*(mean_y_FPN_50[this_div_y, this_div_x]/u_y_tot_50perc[this_div_y, this_div_x]), '.4f')) + "%"
                    print "Mean x FPN of every y at 50% sat level (%): " + str(format(100.0*(mean_x_FPN_50[this_div_y, this_div_x]/u_y_tot_50perc[this_div_y, this_div_x]), '.4f')) + "%"
                    print "Mean y FPN of every x at 50% sat level (DN): " + str(format(mean_y_FPN_50[this_div_y, this_div_x], '.4f')) + "DN"
                    print "Mean x FPN of every y at 50% sat level (DN): " + str(format(mean_x_FPN_50[this_div_y, this_div_x], '.4f')) + " DN"
                    print "Row/Column FPN in x at 50% sat level (%): " + str(format(100.0*(FPN_in_x_50[this_div_y, this_div_x]/u_y_tot_50perc[this_div_y, this_div_x]), '.4f')) + "%"
                    print "Row/Column FPN in y at 50% sat level (%): " + str(format(100.0*(FPN_in_y_50[this_div_y, this_div_x]/u_y_tot_50perc[this_div_y, this_div_x]), '.4f')) + "%"
                    print "Row/Column FPN in x at 50% sat level (DN): " + str(format(FPN_in_x_50[this_div_y, this_div_x], '.4f')) + "DN"
                    print "Row/Column FPN in y at 50% sat level (DN): " + str(format(FPN_in_y_50[this_div_y, this_div_x], '.4f')) + " DN"

        else:
            # ADC level vs test signal 
            plt.figure()
            plt.title("ADC level vs signal")
            un, y_div, x_div = np.shape(u_y_tot)
            colors = cm.rainbow(np.linspace(0, 1, x_div*y_div))
            color_tmp = 0;
            for this_area_x in range(x_div):
                for this_area_y in range(y_div):
                    plt.plot( exposures[:,this_area_y,this_area_x] , u_y_tot[:,this_area_y,this_area_x] , 'o', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_area_x]) + ', Y: ' + str(frame_y_divisions[this_area_y]) )
                    color_tmp = color_tmp+1
            lgd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            plt.ylabel('ADC level [DN]') 
            plt.xlabel('Voltage value [bit]')
            plt.savefig(figure_dir+"adc_test.pdf",  format='pdf', bbox_extra_artists=(lgd,), bbox_inches='tight') 
            plt.savefig(figure_dir+"adc_test.png",  format='png', bbox_extra_artists=(lgd,), bbox_inches='tight', dpi=1000)
            plt.close("all")
            
            # Temporal noise of ADC 
            plt.figure()
            plt.title("Temporal Noise of ADC")
            un, y_div, x_div = np.shape(sigma_tot)
            colors = cm.rainbow(np.linspace(0, 1, x_div*y_div))
            color_tmp = 0;
            for this_area_x in range(x_div):
                for this_area_y in range(y_div):
                    plt.plot( exposures[:,this_area_y,this_area_x] , sigma_tot[:,this_area_y,this_area_x] , 'o', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_area_x]) + ', Y: ' + str(frame_y_divisions[this_area_y]) )
                    color_tmp = color_tmp+1
            lgd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            plt.ylim([0,1]) 
            plt.ylabel('Temporal noise [DN]') 
            plt.xlabel('Voltage value [bit]')
            plt.savefig(figure_dir+"adc_noise.pdf",  format='pdf', bbox_extra_artists=(lgd,), bbox_inches='tight') 
            plt.savefig(figure_dir+"adc_noise.png",  format='png', bbox_extra_artists=(lgd,), bbox_inches='tight', dpi=1000)
            plt.close("all")
            
        #open report file
        print("Generating report...")
        report_file = figure_dir+"Report_results_APS"+".txt"
        out_file = open(report_file,"w")  
        for this_area_x in range(x_div):
            for this_area_y in range(y_div):
                out_file.write("\n")
                out_file.write("X: " + str(frame_x_divisions[this_area_x]) + ', Y: ' + str(frame_y_divisions[this_area_y])+"\n")           
                out_file.write("FPN at 50% sat level (DN): " + str(format(FPN_50[this_area_y, this_area_x], '.4f')) + " DN\n")
                out_file.write("FPN at 50% sat level (%): " + str(format(100.0*(FPN_50[this_area_y, this_area_x]/u_y_tot_50perc[this_area_y, this_area_x]), '.4f')) + "%\n")
                out_file.write("Mean y FPN of every x at 50% sat level (%): " + str(format(100.0*(mean_y_FPN_50[this_area_y, this_area_x]/u_y_tot_50perc[this_area_y, this_area_x]), '.4f')) + "%\n")
                out_file.write("Mean x FPN of every y at 50% sat level (%): " + str(format(100.0*(mean_x_FPN_50[this_area_y, this_area_x]/u_y_tot_50perc[this_area_y, this_area_x]), '.4f')) + "%\n")
                out_file.write("Mean y FPN of every x at 50% sat level (DN): " + str(format(mean_y_FPN_50[this_area_y, this_area_x], '.4f')) + "DN\n")
                out_file.write("Mean x FPN of every y at 50% sat level (DN): " + str(format(mean_x_FPN_50[this_area_y, this_area_x], '.4f')) + " DN\n")
                out_file.write("FPN in x row/column only at 50% sat level (%): " + str(format(100.0*(FPN_in_x_50[this_area_y, this_area_x]/u_y_tot_50perc[this_area_y, this_area_x]), '.4f')) + "%\n")
                out_file.write("FPN in y row/column only at 50% sat level (%): " + str(format(100.0*(FPN_in_y_50[this_area_y, this_area_x]/u_y_tot_50perc[this_area_y, this_area_x]), '.4f')) + "%\n")
                out_file.write("FPN in x row/column only at 50% sat level (DN): " + str(format(FPN_in_x_50[this_area_y, this_area_x], '.4f')) + "DN\n")
                out_file.write("FPN in y row/column only at 50% sat level (DN): " + str(format(FPN_in_y_50[this_area_y, this_area_x], '.4f')) + " DN\n")
        out_file.write("\n")
        out_file.write("###############################################################################################\n")
        for this_file in range(len(exposures)):
            out_file.write("Exposure " +str(exposures[this_file]) + " us:\n")
            for this_area_x in range(x_div):
                for this_area_y in range(y_div):
                    out_file.write("X: " + str(frame_x_divisions[this_area_x]) + ', Y: ' + str(frame_y_divisions[this_area_y])+"\n")
                    out_file.write("Spatiotemporal mean (DN): " + str(u_y_tot[this_file, this_area_y, this_area_x]) + "\n")
                    out_file.write("Temporal variance (DN^2): " + str(sigma_tot[this_file, this_area_y, this_area_x]) + "\n")
                    out_file.write("Temporal SD (%): " + str(100.0*((sigma_tot[this_file, this_area_y, this_area_x]**0.5)/u_y_tot[this_file, this_area_y, this_area_x])) + "%\n")
                    out_file.write("FPN (DN): " + str(format(FPN_all[this_file, this_area_y, this_area_x], '.4f')) + " DN\n")
                    out_file.write("FPN (%): " + str(format(100.0*(FPN_all[this_file, this_area_y, this_area_x]/u_y_tot[this_file, this_area_y, this_area_x]), '.4f')) + "%\n")
                    out_file.write("Mean y FPN of every x (%): " + str(format(100.0*(mean_y_FPN_all[this_file, this_area_y, this_area_x]/u_y_tot[this_file, this_area_y, this_area_x]), '.4f')) + "%\n")
                    out_file.write("Mean x FPN of every y (%): " + str(format(100.0*(mean_x_FPN_all[this_file, this_area_y, this_area_x]/u_y_tot[this_file, this_area_y, this_area_x]), '.4f')) + "%\n")
                    out_file.write("Mean y FPN of every x (DN): " + str(format(mean_y_FPN_all[this_file, this_area_y, this_area_x], '.4f')) + "DN\n")
                    out_file.write("Mean x FPN of every y (DN): " + str(format(mean_x_FPN_all[this_file, this_area_y, this_area_x], '.4f')) + " DN\n")
                    out_file.write("FPN in x row/column only (%): " + str(format(100.0*(FPN_in_x_all[this_file, this_area_y, this_area_x]/u_y_tot[this_file, this_area_y, this_area_x]), '.4f')) + "%\n")
                    out_file.write("FPN in y row/column only (%): " + str(format(100.0*(FPN_in_y_all[this_file, this_area_y, this_area_x]/u_y_tot[this_file, this_area_y, this_area_x]), '.4f')) + "%\n")
                    out_file.write("FPN in x row/column only (DN): " + str(format(FPN_in_x_all[this_file, this_area_y, this_area_x], '.4f')) + "DN\n")
                    out_file.write("FPN in y row/column only (DN): " + str(format(FPN_in_y_all[this_file, this_area_y, this_area_x], '.4f')) + " DN\n")
            out_file.write("-----------------------------------------------------------------------------------------\n")
        out_file.close()
        print("Saving results...")
        var_dir = ptc_dir+'saved_variables/'
        if(not os.path.exists(var_dir)):
            os.makedirs(var_dir)
            print("Results saved in /saved_variables/")
        np.savez(var_dir+"variables_"+sensor+".npz",exposures=exposures,spatiotemporal_mean=u_y_tot,temporal_var_DN2=sigma_tot,FPN_DN=FPN_all,FPN_in_X_DN=FPN_in_x_all,FPN_in_y_DN=FPN_in_y_all,sensor=sensor,frame_x_divisions=frame_x_divisions,frame_y_divisions=frame_y_divisions)

        if(ptc_dir.lower().find('dark') < 0):
            return i_pd_vs, Gain_uVe_lin
        else:
            return i_pd_vs
        

#        winsound.Beep(500,2000)

    def confIntMean(self, a, conf=0.95):
        mean, sem, m = np.mean(a), st.sem(a), st.t.ppf((1+conf)/2., len(a)-1)
        return mean - m*sem, mean + m*sem

    def ismember(self, a, b):
        '''
        as matlab: ismember
        '''
        # tf = np.in1d(a,b) # for newer versions of numpy
        tf = np.array([i in b for i in a])
        u = np.unique(a[tf])
        index = np.array([(np.where(b == i))[0][-1] if t else 0 for i,t in zip(a,tf)])
        return tf, index
