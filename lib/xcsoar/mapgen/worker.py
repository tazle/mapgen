import os
import sys
import time
import smtplib
import socket
import traceback
from xcsoar.mapgen.job import Job
from xcsoar.mapgen.generator import Generator

class Worker:
    def __init__(self, dir_jobs, dir_data, mail_server):
        self.__dir_jobs = os.path.abspath(dir_jobs)
        self.__dir_data = os.path.abspath(dir_data)
        self.__mail_server = mail_server
        self.__run = False

    def __send_download_mail(self, job):
        try:
            print "Sending download mail to " + job.description.mail + " ..."

            s = smtplib.SMTP(self.__mail_server)
            try:
                msg = "From: no-reply@xcsoar.org" +\
                    "\nTo: " + job.description.mail +\
                    "\nSubject: XCSoar Map Generator - Download ready (" + job.description.name + ".xcm)\n" +\
                    "The XCSoar Map Generator has finished your map.\n" +\
                    "It can be downloaded at http://www.xcsoar.org/mapgen/download?uuid=" + job.uuid +\
                    "\nThis link is valid for 7 days.\n"
                s.sendmail('no-reply@xcsoar.org', job.description.mail, msg)
            finally:
                s.quit()
        except Exception, e:
            print 'Failed to send mail: ' + str(e)

    def __do_job(self, job):
        try:
            print "Generating map file for job " + job.uuid
            description = job.description

            if description.waypoint_file == None and description.bounds == None:
                print "No waypoint file or bounds set. Aborting."
                job.delete()
                return

            generator = Generator(self.__dir_data, job.file_path('tmp'))

            generator.set_bounds(description.bounds)
            generator.add_information_file(job.description.name, job.description.mail)

            if description.use_topology:
                job.update_status('Creating topology files...')
                generator.add_topology()

            if description.use_terrain:
                job.update_status('Creating terrain files...')
                generator.add_terrain(description.resolution)

            if description.waypoint_file:
                job.update_status('Adding waypoint file...')
                generator.add_waypoint_file(job.file_path(description.waypoint_file))

            if description.waypoint_details_file:
                job.update_status('Adding waypoint details file...')
                generator.add_waypoint_details_file(job.file_path(description.waypoint_details_file))

            if description.airspace_file:
                job.update_status('Adding airspace file...')
                generator.add_airspace_file(job.file_path(description.airspace_file))

            job.update_status('Creating map file...')

            try:
                generator.create(job.map_file())
            finally:
                generator.cleanup()

            os.rmdir(job.file_path('tmp'))
            job.done()
        except Exception, e:
            print 'Error: ' + str(e)
            traceback.print_exc(file=sys.stdout)
            job.error()
            return

        print "Map ready for use (" + job.map_file() + ")"
        if job.description.mail != '':
            self.__send_download_mail(job)

    def run(self):
        self.__run = True
        print "Monitoring " + self.__dir_jobs + " for new jobs ..."
        while self.__run:
            try:
                job = Job.get_next(self.__dir_jobs)
                if job == None:
                    time.sleep(0.5)
                    continue
                self.__do_job(job)
            except Exception, e:
                print 'Error: ' + str(e)
                traceback.print_exc(file=sys.stdout)
