FROM python:3-onbuild

MAINTAINER Loric Brevet <loric.brevet@smile.fr>

RUN apt-get update && apt-get -y install cron

VOLUME ["/usr/src/app"]

# Add crontab file in the cron directory
ADD crontab /etc/cron.d/lbc-cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/lbc-cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Run the command on container startup
CMD cron && tail -f /var/log/cron.log
