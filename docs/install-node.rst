-Installation of a development node machine
-==========================================
-
-.. highlight:: bash
-

Preparation
-----------

First create a new Ubuntu 12.04 LTS instance. Set up git.. TODO


Setting up required software
----------------------------
Update package list and install the required softwares::

  $ sudo apt-get update
  $ sudo apt-get install --yes python-pip virtualenvwrapper git python-dev \
  openvswitch-common openvswitch-datapath-dkms openvswitch-switch \
  openvswitch-controller libvirt-bin python-libvirt \
  libxml2-dev libxslt1-dev zlib1g-dev qemu-kvm

Configuring network
-------------------
Configure Open vSwitch bridge that handle vitual connections::

  $ sudo ovs-vsctl add-br cloud

Enable passwordless Open vSwitch commands::

  $ TODO

Configuring the libvirt daemon
------------------------------
Change the libvirt default settings in */etc/libvirt/qemu.conf*::

  $ sudo tee -a /etc/libvirt/qemu.conf <<A
  clear_emulator_capabilities = 0
  user = "root"
  group = "root"
  cgroup_device_acl = [
  "/dev/null", "/dev/full", "/dev/zero",
  "/dev/random", "/dev/urandom",
  "/dev/ptmx", "/dev/kvm", "/dev/kqemu",
  "/dev/rtc", "/dev/hpet", "/dev/net/tun",
  ]
  A

Setting up SSL certificates for migrations::

  Add "-l" parameter to /etc/default/libvirt-bin at libvirtd-opts="-d -l"
  
  /etc/libvirt/libvirtd.conf
  listen_tcp = 1
  auth_tcp = "none"

  $ TODO

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
  export AMQP_URI=amqp://cloud:password@$(hostname)/circle
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