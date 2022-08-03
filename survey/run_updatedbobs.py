#!/usr/bin/env python3
# This script query the LTA and populate the field and field_obs table
# At the same time set to "Observed" all fields that have at least 3 observed hours

import os, sys, argparse, re
from LiLF.surveys_db import SurveysDB
from astropy.table import Table
import numpy as np

gridfile = 'allsky-grid.fits'

parser = argparse.ArgumentParser(description='Stage and download MS from the LOFAR LTA.')
parser.add_argument('--gridfile', '-g', dest="gridfile", help='The gridfile as created with update_allsky-grid.py', default=gridfile)
parser.add_argument('--skip', '-s', action="store_true", help='Skip observations already present in field_obs, \
        this is faster but might miss some target to update as "Observed" in the field table.')
parser.add_argument('--showdb', '-d', action="store_true", help='Print all targets and exit.')
parser.add_argument('--reset', '-r', dest="reset", help='If "all" reset the db to "Not started" for all fields. If a field is specified it only reset it to "Observed".', default=None)
parser.add_argument('--incompletereset', '-i', action="store_true", help='Reset the fields that are not "Done"/"Not started" to "Observed".')
args = parser.parse_args()

if args.showdb:
    with SurveysDB(survey='lba',readonly=True) as sdb:
        sdb.execute('SELECT id,status,priority FROM fields WHERE status="Observed" order by priority desc')
        r = sdb.cur.fetchall()
        sdb.execute('SELECT field_id FROM field_obs')
        all_fields = [x['field_id'] for x in sdb.cur.fetchall()]
        for i, entry in enumerate(r):
            hrs = sum(np.array(all_fields) == entry['id'])
            print('%03i) ID: %s - %i hrs (%s - priority: %i)' % (i, entry['id'], hrs, entry['status'], entry['priority']))
        print("############################")
        sdb.execute('SELECT * FROM fields WHERE status!="Observed" and status!="Not started"')
        r = sdb.cur.fetchall()
        for i, entry in enumerate(r):
            print('%03i) ID: %s (%s)' % (i, entry['id'], entry['status']))
    sys.exit()

if args.reset is not None:
    with SurveysDB(survey='lba',readonly=False) as sdb:  
        if args.reset == 'all':
            print("WARNING: RESET ALL POINTINGS to \"Not started\"")
            input("Press Enter to continue...")
            sdb.execute('UPDATE fields SET status="Not started"')
            sdb.execute('DELETE from field_obs')
        else:
            print("WARNING: reset pointing %s to \"Observed\"" % args.reset)
            input("Press Enter to continue...")
            sdb.execute('UPDATE fields SET status="Observed" where id="%s"' % args.reset)
        sys.exit()

if args.incompletereset:
    with SurveysDB(survey='lba',readonly=False) as sdb:  
        print("WARNING: RESET INCOMPLETE POINTINGS to \"Observed\"")
        input("Press Enter to continue...")
        sdb.execute('UPDATE fields SET status="Observed" where status!="Done" and status!="Not started"')
        sys.exit()

skip_obs = args.skip

# get obs_id already done
with SurveysDB(survey='lba',readonly=True) as sdb:
    sdb.execute('select obs_id from field_obs')
    obs_to_skip = [ x['obs_id'] for x in sdb.cur.fetchall() ]
print('The following obs are already in the DB:', obs_to_skip)

grid = Table.read('allsky-grid.fits')

with SurveysDB(survey='lba',readonly=False) as sdb:
    for field in grid:
        field_id = field['name']
        nobs = field['hrs']
        for obs_id, cycle in zip(field['obsid'],field['cycle']):
            if obs_id != 0 and cycle != 'bad' and cycle != 'bug' and not obs_id in obs_to_skip:
                print('Add to the db: %i -> %s' % (obs_id, field_id))
                sdb.execute('INSERT INTO field_obs (obs_id,field_id) VALUES (%i,"%s")' % (obs_id, field_id))
            if nobs >= 3:
                print("%s: set as observed (%i)" % (field_id, nobs))
                sdb.execute('UPDATE fields SET status="Observed" WHERE id="%s"' % (field_id))
                if nobs > 7:
                    sdb.execute('UPDATE fields SET priority=2 WHERE id="%s"' % (field_id))
                else:
                    sdb.execute('UPDATE fields SET priority=1 WHERE id="%s"' % (field_id))

#with SurveysDB(survey='lba',readonly=False) as sdb:
#    for project in projects:
#        print('Checking project: %s' % project)
#        query_observations = Observation.select_all().project_only(project)
#        for observation in query_observations:
#            obs_id = int(observation.observationId)
#            id_all[obs_id]=[]
#
#            # this is faster but doesn't allow to count how many obs per target are available and may result
#            # in not setting a target as "Observed" below
#            if skip_obs and obs_id in obs_to_skip: continue
#
#            print('Checking obs_id: %i' % obs_id)
#            dataproduct_query = CorrelatedDataProduct.observations.contains(observation)
#            # isValid = 1 means there should be an associated URI
#            dataproduct_query &= CorrelatedDataProduct.isValid == 1
#            dataproduct_query &= CorrelatedDataProduct.minimumFrequency >= 59
#            dataproduct_query &= CorrelatedDataProduct.maximumFrequency <= 59.3
#            for i, dataproduct in enumerate(dataproduct_query):
#                # apply selections
#                field_id = dataproduct.subArrayPointing.targetName.split('_')[-1]
#                time = dataproduct.subArrayPointing.startTime
#                if not obs_id in obs_to_skip: # prevent multiple entries
#                    print('Add to the db: %i -> %s' % (obs_id, field_id))
#                    sdb.execute('INSERT INTO field_obs (obs_id,field_id) VALUES (%i,"%s")' % (obs_id, field_id))
#                id_all[obs_id].append(field_id)
#
#field_id_all = []
#for obs_id, field_id in id_all.items():
#    field_id_all += field_id
#
#with SurveysDB(survey='lba',readonly=False) as sdb:
#    for field_id in set(field_id_all):
#        nobs = 
#        # 3 hrs are the minimum to have an observation marked as "Observed"
#        if nobs >= 3:
#            print("Set %s as observed (%i)" % (field_id, nobs))
#            sdb.execute('UPDATE fields SET status="Observed" WHERE id="%s"' % (field_id))
#            if nobs > 7:
#                sdb.execute('UPDATE fields SET priority=2 WHERE id="%s"' % (field_id))
#            else:
#                sdb.execute('UPDATE fields SET priority=1 WHERE id="%s"' % (field_id))
