import matplotlib.pyplot as plt
import numpy as np
import cartopy.crs as ccrs
import pyshtools as pysh
from numpy import pi as pi
from scipy.special import sph_harm
from scipy import interpolate 
sentinel = object()


if __name__ == "__main__":
    pass

#########################################################
# set some constants
b    = 6371000.          # mean radius of the Earth
g    = 9.81              # mean surface gravity
G    = 6.674e-11         # gravitational constant
rhow = 1000.0            # density of water
rhoi =  917.0            # density of ice
CC = 8.038e37            # polar moment of inertia 
AA = 8.012e37            # equatorial moment of inertia
Om = 2.*pi/(24.*3600.)   # mean rotation rate
Me = 5.974e24            # mass of the Earth
##########################################################


##########################################################
# set some options
ep = 0.001               # tolerance for iterations
kind = 'complex'         # type of fields
csphase = -1             # Condon Shortley Phase
normalization = 'ortho'  # normalisation convention
##########################################################


######################################################################
# function to plot geographic data on GL grid. If complex data is
# input, only the real part is plotted
def geo_plot(data,cstring):
    ax = plt.axes(projection=ccrs.PlateCarree())
    plt.pcolormesh(data.lons()-180,data.lats(),np.real(data.data),shading = 'gouraud',cmap=cstring)
    ax.coastlines()
    plt.colorbar()
    plt.show()
    return


######################################################################
# function to read in present sea level and ice thickness and
# interpolate onto GL-grid (from ice6g0.dat)
def get_sl_ice_data(L):

    # initialise the grids
    sl = pysh.SHGrid.from_zeros(lmax=L,grid='GLQ',kind=kind)
    ice = sl.copy()
    
    dat = np.loadtxt('data/ice6g0.dat')

    nlat = int(dat[0,0])
    nlon = int(dat[0,1])
    
    sld = np.zeros([nlat,nlon],dtype = complex)
    latd = np.zeros([nlat,nlon])
    lond = np.zeros([nlat,nlon])
    icd = np.zeros([nlat,nlon],dtype = complex)

        
    k = 0
    for ilon in range(nlon):
        for ilat in range(nlat):
            k = k + 1
            latd[ilat,ilon] = dat[k,1]
            lond[ilat,ilon] = dat[k,0]+180.
            icd[ilat,ilon] = dat[k,2]
            sld[ilat,ilon] = -dat[k,3]
             
    
    # form the interpolating function for SL
    fun = interpolate.interp2d(lond[0,:],latd[:,0],np.real(sld),kind='linear')
    nlatgrid = sl.nlat
    nlongrid = sl.nlon
    lat = sl.lats()
    lon = sl.lons()
    
    # interpolate onto sl grid
    for ilat in range(nlatgrid):
        for ilon in range(nlongrid):
            sl.data[ilat,ilon] = fun(lon[ilon],lat[ilat])


    # form the interpolating function for ice
    fun = interpolate.interp2d(lond[0,:],latd[:,0],np.real(icd),kind='linear')
    

    #interpolate onto ice grid
    for ilat in range(nlatgrid):
        for ilon in range(nlongrid):
            ice.data[ilat,ilon] = fun(lon[ilon],lat[ilat])
            
    # correct sl where there is land-based ice
    #sl = sl + ice
    for ilat in range(nlatgrid):
        for ilon in range(nlongrid):
            if(ice.data[ilat,ilon] > 0 and sl.data[ilat,ilon] < 0):
                sl.data[ilat,ilon] = sl.data[ilat,ilon] + ice.data[ilat,ilon]
        
    return sl,ice               



###################################################################
# integrates a function over the surface
def surface_integral(fun):
    fun_lm = fun.expand(normalization=normalization,csphase=csphase)
    int = np.sqrt(4*pi)*b*b*np.real(fun_lm.coeffs[0,0,0])
    return int


###################################################################
# integrates a function over the oceans
def ocean_integral(C,fun):
    tmp    = C*fun
    tmp_lm = tmp.expand(normalization=normalization,csphase=csphase)
    int = np.sqrt(4*pi)*b*b*np.real(tmp_lm.coeffs[0,0,0])
    return int


###################################################################
# function that returns the ocean function and ocean area
def ocean_function(sl,ice):
    C = sl.copy()
    nth = sl.nlat
    nph = sl.nlon
    th = np.radians(90-sl.lats())
    ph = np.radians(sl.lons())
    
    # set the ocean function
    for ith in range(nth):
        for iph in range(nph):            
            sll  = sl.data[ith,iph] 
            icel = ice.data[ith,iph]            
            if(rhow*sll - rhoi*icel >= 0.): 
                C.data[ith,iph] = 1.
            else:
                C.data[ith,iph] = 0.

    return C



#############################################################
# function to read in the generalised Love numbers from a file
# and return them up to the required degree
def get_love_numbers(L):
    data = np.loadtxt('data/love_U.dat')
    hu = data[0:L+1,1]
    ku = data[0:L+1,3]
    data = np.loadtxt('data/love_P.dat')
    hp = data[0:L+1,1]
    kp = data[0:L+1,3]
    return hu,ku,hp,kp


#############################################################
# sets a spatial grid's values to zero in the southern
# hemisphere
def zero_southern_hemisphere(fin):
    nlat = fin.nlat
    lats = fin.lats()
    fout = fin.copy()
    for ilat in range(nlat):
        lat = lats[ilat]
        if(lat < 0.):
            fout.data[ilat,:] = 0.    
    return fout


#############################################################
# sets a spatial grid's values to zero in the northern
# hemisphere
def zero_northern_hemisphere(fin):
    nlat = fin.nlat
    lats = fin.lats()
    fout = fin.copy()
    for ilat in range(nlat):
        lat = lats[ilat]
        if(lat > 0.):
            fout.data[ilat,:] = 0.    
    return fout


#############################################################
# function to compute centrifugal potential perturbation
def centrifugal_perturbation(Dphi_lm,Dpsi_lm):

    
    # compute the inertia tensor perturbations
    DIxz = -np.sqrt(5./(6.*pi))*(b**3/G)*np.real(Dphi_lm.coeffs[0,2,1])
    DIyz = -np.sqrt(5./(6.*pi))*(b**3/G)*np.imag(Dphi_lm.coeffs[0,2,1])

    # set the perturbed rotation rates
    DOmx = Om*DIxz/(CC-AA)
    DOmy = Om*DIyz/(CC-AA)
        
    # set the coefficients for the centrifugal potential perturbation
    Dpsi_lm.coeffs[1,2,1] = b**2*Om*np.sqrt((2.*pi)/15.)*( DOmx + 1j*DOmy)
    Dpsi_lm.coeffs[0,2,1] = b**2*Om*np.sqrt((2.*pi)/15.)*(-DOmx + 1j*DOmy)
    
    return
    


##############################################################
# function to solve the generalised fingerprint problem for a
# given displacement and potential loads
def generalised_fingerprint(C,zeta,zeta_u,zeta_p,rotation=True):

    # get the maximum degree
    L = C.lmax

    # get the ocean area
    A = surface_integral(C)
    
    # get the love numbers
    data = np.loadtxt('data/love.dat')
    hu = data[:L+1,1]
    hp = data[:L+1,3]
    ku = data[:L+1,2]
    kp = data[:L+1,4]
    h = hu + hp
    k = ku + kp
    ht = data[2,5]
    kt = data[2,6]
    
    # calculate the average change in sea level
    Mload = surface_integral(zeta)
    slu  = -Mload/(rhow*A)
    onegrid = pysh.SHGrid.from_zeros(lmax=L,grid='GLQ',kind=kind)
    onegrid.data[:,:] = 1.
    sl = slu*onegrid


    # initialise displacement and potential perturbations
    u_lm   = pysh.SHCoeffs.from_zeros(lmax=sl.lmax,normalization=normalization,kind=kind,csphase=csphase)
    phi_lm = u_lm.copy()
    psi_lm = u_lm.copy()

    # store the initial guess
    sl0 = sl.copy()
    err = 1.

    # start the iterations
    it = 0
    while(err > ep):

        it = it+1
        
        # compute the current loads
        sigma = rhow*C*sl + zeta
        sigma_lm  = sigma.expand(normalization=normalization,csphase=csphase)
        zeta_u_lm = zeta_u.expand(normalization=normalization,csphase=csphase)
        zeta_p_lm = zeta_p.expand(normalization=normalization,csphase=csphase)        
        
        # determine the response to the loading
        for l in range(L+1):
            u_lm.coeffs[:,l,:]   =   h[l]*sigma_lm.coeffs[:,l,:]  \
                                    + hu[l]*zeta_u_lm.coeffs[:,l,:] \
                                    + hp[l]*zeta_p_lm.coeffs[:,l,:]

            phi_lm.coeffs[:,l,:] =   k[l]*sigma_lm.coeffs[:,l,:]  \
                                    + ku[l]*zeta_u_lm.coeffs[:,l,:] \
                                    + kp[l]*zeta_p_lm.coeffs[:,l,:] 
        

        # add in the centrifugal contribution
        u_lm.coeffs[:,2,:]   = u_lm.coeffs[:,2,:]   + ht*psi_lm.coeffs[:,2,:]
        phi_lm.coeffs[:,2,:] = phi_lm.coeffs[:,2,:] + kt*psi_lm.coeffs[:,2,:]

        # get the centrifugal potential perturbation
        if(rotation):
            centrifugal_perturbation(phi_lm,psi_lm)

        # get the spatial fields
        u   =   u_lm.expand(grid='GLQ')
        phi = phi_lm.expand(grid='GLQ')
        psi = psi_lm.expand(grid='GLQ')


        # update the sea level
        int    = ocean_integral(C,g*u + phi + psi)
        sl    = -1.*(g*u + phi + psi)/g +(int/(g*A) + slu)*onegrid

        # get the change since the last iteration
        err = np.max(np.abs(sl.data - sl0.data))/np.abs(slu)

        print('iteration = ',it,'relative change = ',err)
        
        # store the most recent solution
        sl0 = sl.copy()
        
        
    return sl,u,phi,psi



##############################################################
# function to solve the fingerprint problem for a given change
# in ice thickness
def fingerprint(C,ice,rotation=True):
    L = C.lmax
    zeta   = rhoi*(1.-C)*ice
    zeta_u = pysh.SHGrid.from_zeros(lmax=L,grid='GLQ',kind=kind)
    zeta_p = pysh.SHGrid.from_zeros(lmax=L,grid='GLQ',kind=kind)
    return generalised_fingerprint(C,zeta,zeta_u,zeta_p,rotation)


