.PHONY: start stop restart status doctor logs panel daemon daemon-stop monitor help

help:
	@bin/reachy-app help

start:
	@bin/reachy-app start

stop:
	@bin/reachy-app stop

restart:
	@bin/reachy-app restart

status:
	@bin/reachy-app status

doctor:
	@bin/reachy-app doctor

logs:
	@bin/reachy-app logs

panel:
	@bin/reachy-app panel

monitor:
	@bin/cve-monitor --interval 60

daemon:
	@bin/reachy-app daemon

daemon-stop:
	@bin/reachy-app daemon-stop
