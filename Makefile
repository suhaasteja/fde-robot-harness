.PHONY: start stop restart status doctor logs panel help

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
