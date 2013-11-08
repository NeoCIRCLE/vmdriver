Installation of a development node machine
==========================================

.. highlight:: bash

Preparation
-----------

First create a new Ubuntu 12.04 LTS or later instance. Set up git.. TODO


Setting up required software
----------------------------
Update package list and install the required softwares::

  $ sudo apt-get update
    sudo apt-get install --yes python-pip virtualenvwrapper git python-dev \
    openvswitch-common openvswitch-datapath-dkms openvswitch-switch \
    openvswitch-controller libvirt-bin python-libvirt \
    libxml2-dev libxslt1-dev

Configuring network
-------------------
Configure Open vSwitch bridge that handle vitual connections::
  $ sudo ovs-vsctl add-br cloud

Installing CIRCLE vmdriver
--------------------------
Clone the git repository::

  $ git clone git@git.cloud.ik.bme.hu:circle/vmdriver.git vmdriver

Set up virtualenv profile::

  $ source /etc/bash_completion.d/virtualenvwrapper
  $ mkvirtualenv vmdriver

Save configuration to virtualenv and activate environment::

  $ cat >>/home/cloud/.virtualenvs/vmdriver/bin/postactivate <<END
  export LIBVIRT_KEEPALIVE=True
  export LIBVIRT_URI=test:///default
  export AMQP_URI=amqp://cloud:password@host/circle
  export HYPERVISOR_TYPE=test 
  END

Copy the libvrit bindings to the local virtualenv directory::

  $  cp /usr/lib/python2.7/dist-packages/*libvirt* ~/.virtualenvs/vmdriver/lib/python2.7/site-packages/
 
Install the required python packages::

  $ pip install -r requirements/test.txt

Copy the upstart scripts for celery services::

  $ sudo cp miscellaneous/vmcelery.conf /etc/init/
  $ sudo cp miscellaneous/netcelery.conf /etc/init/

Start celery daemons::

  $ sudo start vmcelery
  $ sudo start netcelery


