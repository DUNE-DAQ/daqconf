# OKS Configuration Generation
This repository contains scripts for generating OKS database files.

## createOKSdb

   A script that generates an 'empty' OKS database, just containging
the include files for the core schema and any other schema/data files
you specify on the commad line.

## oks_enable

  Add Resource objects to or remove from the `disabled` relationship
of a Session

## dromap2oks
  Convert a JSON readout map file to an OKS file.

## generate_readoutOKS

  Create an OKS configuration file defining ReadoutApplications for
  all readout groups defined in a readout map.
