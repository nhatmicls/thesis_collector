# NATSIO

Code use natsio and queue for upload data to server

## Requirements

- Python 3.9
- queue
- persistqueue
- pykka
- rx
- modbus_lib

## Verifying the Natsio Installation

Command:
```
python -m unittest discover -v natsio
```

Expected result:
```
test_store_data_from_ram_to_disk (natsio.test.test_queue.test_data_processor) ... ok
test_store_to_ram (natsio.test.test_queue.test_data_processor) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.016s

OK
```
