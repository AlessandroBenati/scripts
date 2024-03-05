#!/usr/bin/env python

from astropy.io import fits as pyfits
import argparse
import numpy as np

def combine_masks(output_mask, *input_masks):
    # Determine the output mask file path
    if output_mask is None:
        output_mask = "mask.fits"
        
    # Initialize data_comb to an empty array
    data_comb = None

    # Open each input mask file and combine with the output mask
    for input_mask in input_masks:
        with pyfits.open(input_mask) as fits:
            data = fits[0].data
            if data_comb is None:
                data_comb = np.zeros_like(data)
            #data = data.squeeze()
            if data.shape != data_comb.shape:
                print(f"Shapes of input mask {input_mask} and output mask {output_mask} are different:")
                print(f"Shape of input mask: {data.shape}")
                print(f"Shape of output mask: {data_comb.shape}")
            assert data.shape == data_comb.shape
            data_comb[(data == 1.)] = 1.

    # Write the combined data to the output mask file
    pyfits.writeto(output_mask, data_comb, overwrite=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine multiple masks using pixel-by-pixel 'OR' operation")
    parser.add_argument("-o", "--output_mask", help="Name of the output mask file (default: mask.fits)", default=None)
    parser.add_argument("input_masks", nargs="+", help="Paths to the input mask files")

    args = parser.parse_args()

    combine_masks(args.output_mask, *args.input_masks)
