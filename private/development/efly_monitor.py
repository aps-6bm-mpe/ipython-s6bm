from epics import caget, caput, cainfo
import epics
import time

# get the required PV
campv = epics.PV('1idPG2:cam1:TriggerMode')
counterpv = epics.PV('1idPG2:cam1:NumImagesCounter_RBV')

flag = 1
seq = 1

while flag is 1:
	i = 0
	new_scan = 0
	while campv.get() == 3:
		# start monitor image counts during FlyScan
		counter = counterpv.get() 
		t0 = time.time()
		new_scan = 1
		bad_scan = 0
		if i == 0: 
			print(f'{time.ctime()}, Flyscan {seq: 4d} has started, {counter} images collected') 
		i += 1 
		time.sleep(5) 

		while (counterpv.get() - counter) == 0 and campv.get() == 3:
			duration = time.time()-t0
			print(f'scan {seq: 4d} failed, image counter stucked at {counter} images for {duration} seconds')
			if duration > 60:
				# 60 seconds without image, scan must be dead.
				bad_scan = 1
				print(f'Sending internal trigger to abort scan {seq: 4d}')
				# switch to internal trigger to finish the scan
				campv.put(0)
			time.sleep(30)
			
		if bad_scan == 1:
			time.sleep((1801-counter)/18+5)
		else:
			time.sleep(1)
			
	if new_scan == 1:
		print(f'{time.ctime()}, Flyscan {seq:4d} has finished.') 
		seq += 1

	time.sleep(1)
	
