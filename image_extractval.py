#!/usr/bin/python
# Extract freq flux rms from a series of images
# likely prepared with image_armonize.py

import sys, os, math
import optparse
import numpy as np
import pyrap.images
import pyrap.tables

import linearfit

def getValues(imglist):
    """Read image pixel values
    """
    values = []
    print "Reding images values."
    for imgname in imglist:
        try:
            image = pyrap.images.image(imgname)
            values.append(np.squeeze(np.array(image.getdata())))
        except:
            print "ERROR: error accessing iamges data, probably wrong name or data format"
            exit(1)
    # check if shapes are consinstent
    shape = values[0].shape
    for val in values[1:]:
        assert(val.shape == shape)
    return values, shape

def getRmsMask(shape, rmsmask=None):
    """Read RMS mask
    """
    if (rmsmask != None):
        print "Reading RMS mask = "+rmsmask
        image = pyrap.images.image(rmsmask)
        rmsmaskval = np.squeeze(np.array(image.getdata()))
    else:
        print "Assuming RMS mask = all"
        rmsmaskval = np.ones(shape)
    assert rmsmaskval.shape == shape
    return rmsmaskval

def getFluxMask(shape, fluxmask=None):
    """Read flux mask
    """
    if (fluxmask != None):
        print "Reading flux mask = "+fluxmask
        image = pyrap.images.image(fluxmask)
        fluxmaskval = np.squeeze(np.array(image.getdata()))
    else:
        print "Assuming flux mask = inner quarter"
        fluxmaskval = np.zeros(shape)
        # set the inner half to be the mask
        fluxmaskval[len(fluxmaskval)/4:3*len(fluxmaskval)/4,\
                len(fluxmaskval[0])/4:3*len(fluxmaskval[0])/4] = 1
    assert fluxmaskval.shape == shape
    return fluxmaskval

def calcRms(values, rmsmask, fluxmaskval = None, n_sigma = 5):
    """Calculating RMSs and set to 0 the values under n sigma
    """
    rmsvalues = []
    print "Calculating RMS."
    for val in values:
        rms = np.std(val[np.where(rmsmaskval == 1)])
        rmsvalues.append(rms)
        if fluxmaskval != None:
            fluxmaskval[np.where(val < n_sigma*rms)] = 0
    return rmsvalues, fluxmaskval

def calcFluxes(values, fluxmaskval, beam, dpix):
    """Calculate fluxes
    """
    print "Get fluxes."
    fluxvalues = []
    for val in values:
        flux = np.sum(val[np.where(fluxmaskval == 1)])/((1.1331*beam[0]*beam[1])/(dpix[0]*dpix[1]))
        fluxvalues.append(flux)
    return fluxvalues

def getFreqs(imglist):
    """Get the image frequencies
    """
    print "Get frequencies."
    freqs = []
    for img in imglist:
        t = pyrap.tables.table(img, ack=False)
        freq = t.getkeyword('coords.worldreplace2')[0]
        freqs.append(freq)
        del t
    return freqs

def getPix(imglist):
    """Get the pixel area (check that is the same)
    """
    print "Get pixels dimensions."
    t = pyrap.tables.table(imglist[0], ack=False)
    dpix = abs(t.getkeyword('coords.direction0.cdelt')*(180/np.pi)*3600) # in arcsec
    del t
    for img in imglist[1:]:
        t = pyrap.tables.table(img, ack=False)
        thisdpix = abs(t.getkeyword('coords.direction0.cdelt')*(180/np.pi)*3600) # in arcsec
        assert(dpix[0] == thisdpix[0] and dpix[1] == thisdpix[1])
        del t
    return dpix

def getBeam(imglist):
    """Get the images beam (check that is the same)
    """
    print "Get beams."
    t = pyrap.tables.table(imglist[0], ack=False)
    bmaj = t.getkeyword('imageinfo.restoringbeam.major.value')
    bmin = t.getkeyword('imageinfo.restoringbeam.minor.value')
    assert t.getkeyword('imageinfo.restoringbeam.major.unit') == 'arcsec'
    assert t.getkeyword('imageinfo.restoringbeam.minor.unit') == 'arcsec'
    del t
    for img in imglist[1:]:
        t = pyrap.tables.table(img, ack=False)
        thisbmaj = t.getkeyword('imageinfo.restoringbeam.major.value')
        thisbmin = t.getkeyword('imageinfo.restoringbeam.minor.value')
        if (round(bmaj) != round(thisbmaj) or round(bmin) != round(thisbmin)):
            print "WARNING: "+img+" has a different beam ("+str(thisbmaj)+","+str(thisbmin)+")!"
        del t
    return [bmaj,bmin]

if __name__ == "__main__":
    opt = optparse.OptionParser(usage="%prog images", version="%prog 0.1")
    opt.add_option('-o', '--outfile', help='Output text file [default = None]', default=None)
    opt.add_option('-p', '--outplot', help='Name of the output plot [default = None]', default=None)
    opt.add_option('-r', '--rmsmask', help='Mask tp compute rms [default = use all]', default=None)
    opt.add_option('-f', '--fluxmask', help='Mask tp compute flux [default = use inner half]', default=None)
    opt.add_option('-e', '--effmask', help='Output effective mask (intersection between fluxmask and pixels > Nsigma*RMS) [default = None]', default=None)
    opt.add_option('-k', '--rescale', help='File with rescaling values to multiply [imgname rescaling] [default = None]', default=None)
    opt.add_option('-s', '--Nsigma', help='Remove a pixel if it is below this sigma in any image [default = 0]', default=0, type='float')
    opt.add_option('-l', help='Output plot shows the log10 of the values', action="store_true", dest="log")
    (options, imglist) = opt.parse_args()
    if len(imglist) == 0: sys.exit("Missing images.")

    outfile = options.outfile
    if options.outfile != None: print "Output file = "+outfile
    outplot = options.outplot
    if options.outplot != None: print "Output plot = "+outplot
    if options.rmsmask != None: rmsmask = options.rmsmask.strip("/")
    if options.fluxmask != None: fluxmask = options.fluxmask.strip("/")
    effmask = options.effmask
    rescalefile = options.rescale
    n_sigma = options.Nsigma
    log = options.log

    values, shape = getValues(imglist)
    rmsmaskval = getRmsMask(shape, rmsmask)
    fluxmaskval = getFluxMask(shape, fluxmask)
    freqs = getFreqs(imglist)
    beam = getBeam(imglist)
    dpix = getPix(imglist)

    # calc rms and mask bad pixels
    maskedpix_pre = float(len(np.where(fluxmaskval == 1)[0]))
    maskedpix_tot = float(len(fluxmaskval[0])*len(fluxmaskval[1]))
    rmsvalues, fluxmaskval = calcRms(values, rmsmaskval, fluxmaskval, n_sigma)
    maskedpix_aft = float(len(np.where(fluxmaskval == 1)[0]))
    print "Mask moved from", maskedpix_pre/maskedpix_tot*100, "% to", maskedpix_aft/maskedpix_tot*100, "%."

    fluxvalues = calcFluxes(values, fluxmaskval, beam, dpix)

    if rescalefile != None:
        rescaleData = np.loadtxt(rescalefile, comments='#', dtype=np.dtype({'names':['img','rescale'], 'formats':['S100',float]}))
        for i, img in enumerate(imglist):
            if img in rescaleData['img']:
                r = rescaleData['rescale'][np.where(rescaleData['img'] == img)]
                fluxvalues[i] *= r
                print "Rescaling", img, "flux by", r

    if outfile != None:
        print "Save flux values in "+outfile
        np.savetxt(outfile, np.array([freqs,fluxvalues,rmsvalues]).transpose(), fmt='%f %f %f')

    if outplot != None:
        data = {'flux':np.array(fluxvalues),'freq':np.array(freqs),'rms':np.array(rmsvalues)}
        if log:
            linearfit.plotlinax(data, outplot)
        else:
            linearfit.plotlogax(data, outplot)

    if effmask != None:
        print "Writing effective mask:"
        if os.path.isdir(effmask): os.system('rm -r '+effmask)
        os.system('cp -r '+imglist[0]+' '+effmask)
        image = pyrap.images.image(effmask)
        val = np.array(image.getdata())
        val[:] = 0
        val[0][0][np.where(fluxmaskval == 1)] = 1 
        image.putdata(val)

    print "Done."
