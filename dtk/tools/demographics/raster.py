'''
Utilities for reading and plotting GeoTIFF binary files.
'''
import os
import json
import sys
import random
import pandas as pd

try:
    import osr
    import gdal
    import gdalconst
except:
    sys.exit('Install required GDAL package: https://pypi.python.org/pypi/GDAL/')
import struct
try:
    import numpy as np
    from numpy import ma
except:
    sys.exit('Install required numpy package: https://pypi.python.org/pypi/numpy/')
try:
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from matplotlib.colors import LogNorm
except:
    sys.exit('Install required matplotlib package: https://pypi.python.org/pypi/matplotlib/')
try:
    from scipy import ndimage
    #http://scipy-lectures.github.io/advanced/image_processing/#edge-detection
except:
    sys.exit('Install required scipy package: https://pypi.python.org/pypi/scipy/')
try:
    from skimage.feature import blob_doh,blob_dog
    from skimage.exposure import adjust_log, rescale_intensity
    from skimage.morphology import watershed
except:
    sys.exit('Install required scipy package: https://pypi.python.org/pypi/scikit-image/')

from node import Node
from visualize_nodes import get_country_shape,plot_geojson_shape


def read(bingrid_name, cropX=None, cropY=None):
    '''
    Read the data and meta-data from GeoTIFF
    '''
    if bingrid_name[-4:] != '.tif':
        raise Exception('Expecting .tif extension for GeoTIFF files')

    ds = gdal.Open(bingrid_name, gdalconst.GA_ReadOnly)
    geotransform = ds.GetGeoTransform()
    srs=osr.SpatialReference(wkt=ds.GetProjection())
    srsLatLong = srs.CloneGeogCS()
    coordtransform = osr.CoordinateTransformation(srs,srsLatLong)


    def transform_fn(x,y):
        ulX,cellsizeX,rotateX,ulY,rotateY,cellsizeY = geotransform
        #print('geotransform',ulX,cellsizeX,rotateX,ulY,rotateY,cellsizeY)
        cropY0=cropY[0] if cropY else 0
        cropX0=cropX[0] if cropX else 0
        return coordtransform.TransformPoint((x+cropX0)*cellsizeX+ulX,(y+cropY0)*cellsizeY+ulY)

    nrows = ds.RasterYSize
    rows = cropY if cropY else range(nrows)

    ncols = ds.RasterXSize
    cols = cropX if cropX else range(ncols)

    band = ds.GetRasterBand(1)
    bandtype = gdal.GetDataTypeName(band.DataType)
    format_char={'Float64':'d', # MAP
                 'Float32':'f'} # WorldPop
    A = np.zeros(shape=(len(rows),len(cols)),dtype=np.float32)
    for i,irow in enumerate(rows):
        scanline=band.ReadRaster( cols[0], irow, len(cols), 1, len(cols), 1, band.DataType)
        data = struct.unpack(format_char[bandtype] * len(cols), scanline)
        A[i][:] = data

    return A, transform_fn


def plot(A, title='Raster_Plot',cmap='YlGnBu', norm=LogNorm(vmin=1, vmax=1e3)):
    fig=plt.figure(title + '_WorldPop',figsize=(8,8))
    ax=plt.subplot(111)
    plt.imshow(A, interpolation='nearest', cmap=cmap, norm=norm)
    ax.set(aspect=1)
    ax.set_axis_bgcolor('LightGray')
    cb=plt.colorbar()
    plt.title(title + ' (WorldPop)')
    cb.ax.set_ylabel(r'population ($\mathrm{km}^{-2}$)', rotation=270, labelpad=15)
    plt.tight_layout()

    return ax


def detect_watershed_patches(A,mask=0,validation=False):
    A_copy=np.copy(A)
    A_copy[A_copy<mask]=0
    A_log=adjust_log(A_copy)
    A_norm=rescale_intensity(A_log)
    print('Raster shape (%d,%d)' % A_norm.shape)
    blobs = blob_dog(A_norm, max_sigma=30, threshold=.1)
    print('Detected %d blobs to seed watershed'%len(blobs))
    if validation:
        ax=plot(A_copy,'DetectBlobs')
        for blob in blobs:
            y, x, r = blob
            c = plt.Circle((x, y), r, color='k', linewidth=1, fill=False)
            ax.add_patch(c)
    x, y = np.indices(A_norm.shape)
    markers=np.zeros(A_norm.shape)
    idxs=range(len(blobs))
    random.shuffle(idxs)
    for i,blob in zip(idxs,blobs):
        xb,yb,rb=blob
        mask_circle = (x - xb)**2 + (y - yb)**2 < rb**2
        markers[mask_circle]=i+1
    watershed_patches = watershed(1-A_norm, markers, mask=A_copy)
    if validation:
        plt.figure('Watershed')
        watershed_patches[watershed_patches<1]=np.nan
        plt.imshow(watershed_patches,cmap='Paired')
        plt.tight_layout()
        plt.title('Watershed')
    return watershed_patches, len(blobs)


def detect_contiguous_blocks(A, mask=0, validation=False):
    binary_img = A > mask
    open_img = ndimage.binary_opening(binary_img)
    close_img = ndimage.binary_closing(open_img)
    label_img, n_labels = ndimage.label(close_img)
    print('Found %d contiguous blocks' % n_labels)

    if validation:
        plt.figure('ContiguousBlocks', figsize=(8,7))
        ax=plt.subplot(221)
        plt.title('binary')
        plt.imshow(binary_img, cmap='gray')
        ax=plt.subplot(222)
        plt.title('open')
        plt.imshow(open_img, cmap='gray')
        ax=plt.subplot(223)
        plt.title('close')
        plt.imshow(close_img, cmap='gray')
        ax=plt.subplot(224)
        plt.title('label')
        plt.imshow(label_img, cmap='spectral')

    return label_img, n_labels


def centroids(A,label_img,n_labels,validation=False):
    A[A<0]=0 # correct no data (?) value of -3.4e38 to zero, so sums don't get messed up for cities by the ocean (e.g. Dakar)
    sums = ndimage.sum(A, label_img, range(1, n_labels + 1))
    centroids = ndimage.center_of_mass(A, label_img, range(1, n_labels + 1))

    if validation:
        plt.figure('VillagePopulationHist')
        plt.title('Populations of labeled villages')
        plt.hist(sums, bins=np.logspace(1, 7, num=50), color='navy', alpha=0.6)
        plt.xscale("log")

    return sums,centroids


def compare(A,sums,centroids,title='Raster_Plot',cmap='YlGnBu'):
    yy,xx = zip(*centroids)
    plt.figure('Nodes')
    ax=plt.subplot(111)
    sizes=[min(3e4,5+v/250.) for v in sums]
    plt.title('Assignment of node populations')
    plt.imshow(A, interpolation='nearest', cmap=cmap, norm=LogNorm(vmin=1, vmax=1e3), alpha=0.8)
    plt.scatter(xx,yy,s=sizes, c='gray', vmin=1, vmax=7, alpha=0.5)
    plt.tight_layout()


def make_nodes(sums,centroids,transform_fn,min_pop=100):
    yy,xx = zip(*centroids)
    nodes=[]
    for x,y,pop in zip(xx,yy,sums):
        if not pop > min_pop:
            continue
        #print(x,y,pop)
        lon,lat,alt=transform_fn(x,y)
        n=Node(lat,lon,pop)
        nodes.append(n)
    return nodes


def plot_nodes(nodes,countries):
    plt.figure('LatLonNodes')
    lats,lons,pp=zip(*[x.toTuple() for x in nodes])
    plt.scatter(lons, lats, [30*p/1e4 for p in pp], color='navy', linewidth=0.1, alpha=0.5)
    plt.gca().set_aspect('equal')
    for country in countries:
        country_shape=get_country_shape(country)
        if country_shape:
            plot_geojson_shape(country_shape)
    plt.tight_layout()


def write_nodes(nodes,title):
    if not os.path.exists('cache'):
        os.mkdir('cache')
    with open('cache/raster_nodes_%s.json' % title,'w') as fjson:
        json.dump([n.toDict() for n in nodes], fjson)


def save_all_figs(dirname='figs'):
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    for L in plt.get_figlabels():
        plt.figure(L)
        plt.savefig(os.path.join(dirname,'%s.png' % L))


def coord_pixel_transform(point_lat, point_long):
    # find the lat-long coordinates of the raster image origin, and an arbitrary other point.
    origin_long, origin_lat, origin_alt = transform_fn(0, 0)
    raster_pt_long, raster_pt_lat, raster_pt_origin = transform_fn(0, 100)

    # find the pixel:decimal degree conversion factor
    conversion_factor = 100 / (origin_lat - raster_pt_lat)  # this is the number of pixels per decimal degree

    # find the pixel location of the passed argument
    point_x = (point_long - origin_long) * conversion_factor
    point_y = (origin_lat - point_lat) * conversion_factor

    return point_x, point_y

if __name__ == '__main__':
    main_dir = 'Q:/Malaria/Myanmar/Karen/village_pop/'
    bin_name = 'Q:/Malaria/Myanmar/Karen/village_pop/MMR_ppp_karen_compressed.tif'

    title = 'Karen, Myanmar'
    mask = 0.001

    # crop = (None,None)
    crop = (range(4900, 8500), range(10500, 16100))
    validation = True

    print "reading raster population file"
    A, transform_fn = read(bin_name, *crop)

    print "reading village location file"

    for village_type in ["manual", "auto"]:

        villages = pd.read_csv("{main_dir}/metf_villages/{village_type}_villages_coords.csv".format(main_dir=main_dir,
                                                                                                    village_type=village_type))

        # convert village locations into pixel coordinates
        coords = villages.apply(lambda row: coord_pixel_transform(row['latitude'], row['longitude']), axis=1)
        villages["pixel_x"] = coords.apply(lambda row: row[0])
        villages["pixel_y"] = coords.apply(lambda row: row[1])

        print "plotting"
        plot(A, title="{village_type} Villages".format(village_type=village_type).capitalize(),
             norm=LogNorm(vmin=1, vmax=10))
        plt.scatter(villages.pixel_x, villages.pixel_y, c="ForestGreen", alpha=0.5)

    save_all_figs(dirname='{main_dir}/plots'.format(main_dir=main_dir))
    plt.show()

    HALT

    patches,N=detect_watershed_patches(A, mask, validation=validation)





    #patches,N=detect_contiguous_blocks(A, mask, validation=validation)
    sums,centroids=centroids(A,patches,N,validation=validation)
    compare(A,sums,centroids,title)
    nodes=make_nodes(sums,centroids,transform_fn,min_pop=100)
    plot_nodes(nodes,countries=[title])
    write_nodes(nodes,title)
    save_all_figs()

    plt.show()
