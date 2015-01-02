import collections
import ok
import time

from util import *

GateSetting = collections.namedtuple('Gate', 'epaddr cl op')
DoseSetting = collections.namedtuple('Dose', 'trig_bit epaddr dose_vol dose_rep')

class DeviceError(Exception):
    pass

class PlusMaze(object):
    '''
    Represents the physical plus maze hardware
    '''

    ordered_dirs = ['west', 'north', 'south', 'east']

    BITFILE = 'toplevel.bit'
    POLL_PERIOD = 100 # ms

    # HARDWARE SETTINGS
    #------------------------------------------------------------
    gate_settings = {'north': GateSetting(epaddr=0x02, cl=555, op=1200),
                     'south': GateSetting(epaddr=0x00, cl=580, op=1200),
                     'east' : GateSetting(epaddr=0x03, cl=570, op=1200),
                     'west' : GateSetting(epaddr=0x01, cl=565, op=1200)}

    dose_settings = {'TRIG_EPADDR': 0x40,
                     'REPS_EPADDR': 0x08,
                     'all'  : DoseSetting(trig_bit=0, epaddr=None, dose_vol=None, dose_rep=None),
                     'east' : DoseSetting(trig_bit=4, epaddr=0x07, dose_vol=17000, dose_rep=8),
                     'south': DoseSetting(trig_bit=1, epaddr=0x04, dose_vol=15000, dose_rep=10),
                     'north': DoseSetting(trig_bit=3, epaddr=0x06, dose_vol=15500, dose_rep=12),
                     'west' : DoseSetting(trig_bit=2, epaddr=0x05, dose_vol=15000, dose_rep=7)}

    rotation_settings = {'TRIG_EPADDR': 0x40,
                         'trig_map': {'center ccw': 5,
                                      'center cw' : 6,
                                      'maze ccw': 15, # Unimplemented
                                      'maze cw' : 15, # Unimplemented
                                     }
                        }

    prox_settings = {'LASTDETECT_EPADDR': 0x20,
                     'LASTDETECT_MASK': 0b00000011,
                     'names': {0: 'west',
                               1: 'south',
                               2: 'north',
                               3: 'east'}
                    }


    scope_settings = {'TRIG_EPADDR': 0x40,
                      'trig_map': {'start': 7,
                                   'stop':  8,
                                   'reset': 9,
                                  },
                      'FRAME_LO_EPADDR': 0x21,
                      'FRAME_HI_EPADDR': 0x22,
                     }

    lick_settings = {'TRIG_EPADDR': 0x41,
                     'trig_map': {'reset_addr': 0,
                                 },
                     'PIPE_EPADDR': 0xA0,
                     'BUFFER_LENGTH_IN_BYTES': 2*31250,
                     'LICK_EPADDR': 0x20,
                     'LICK_BIT': 2
                    }

    # CONTINUOUS T-MAZE OPERATION
    #   Description of how to rotate the center platform to accommodate the
    #   path of the mouse. The key ('east', 'north') corresponds to the mouse
    #   moving from east to north, which is a right turn. In this case, we
    #   need to move the T-block counterclockwise
    #------------------------------------------------------------
    pos_to_turn = {('east' , 'north'): 'right',
                   ('north', 'west' ): 'right',
                   ('west' , 'south'): 'right',
                   ('south', 'east' ): 'right',
                   ('east' , 'south'): 'left',
                   ('south', 'west' ): 'left',
                   ('west' , 'north'): 'left',
                   ('north', 'east' ): 'left',
                  }

    turn_compensation = {'right': 'center ccw',
                         'left' : 'center cw',
                        }
    def __init__(self):
        self._initialize_fpga()
        self.setup_dosing()

    def _initialize_fpga(self):
        self.xem = ok.FrontPanel()
        num_devices = self.xem.GetDeviceCount()
        print_msg("Detected {} device{}".format(num_devices,
                                                '' if num_devices==2 else 's'))
        if (num_devices == 0):
            raise DeviceError
        else:
            # FIXME: Always opens the first device
            serial = self.xem.GetDeviceListSerial(0)
            if (self.xem.NoError != self.xem.OpenBySerial(serial)):
                print_msg("FPGA with serial {} could not be opened".format(serial))
                raise DeviceError

            if (self.xem.NoError != self.xem.LoadDefaultPLLConfiguration()):
                print_msg("Unable to set default PLL config")
                raise DeviceError

            if (self.xem.NoError != self.xem.ConfigureFPGA(PlusMaze.BITFILE)):
                print_msg("Failed to load bitfile {}".format(PlusMaze.BITFILE))
                raise DeviceError
            else:
                print_msg("Loaded bitfile {} to {}".format(PlusMaze.BITFILE, serial))

    def setup_dosing(self):
        dose_reps = 0x00
        for d in PlusMaze.ordered_dirs:
            dose_reps += PlusMaze.dose_settings[d].dose_rep << \
                            (4*(PlusMaze.dose_settings[d].trig_bit - 1))
            self.xem.SetWireInValue(PlusMaze.dose_settings[d].epaddr,
                                    PlusMaze.dose_settings[d].dose_vol)
        self.xem.SetWireInValue(PlusMaze.dose_settings['REPS_EPADDR'], dose_reps)
        self.xem.UpdateWireIns()

    def start_recording(self):
        self.xem.ActivateTriggerIn(PlusMaze.scope_settings['TRIG_EPADDR'],
                                   PlusMaze.scope_settings['trig_map']['start'])
        print_msg("Started miniscope recording")

    def stop_recording(self):
        self.xem.ActivateTriggerIn(PlusMaze.scope_settings['TRIG_EPADDR'],
                                   PlusMaze.scope_settings['trig_map']['stop'])
        print_msg("Stopped miniscope recording")

    def reset_scope_counter(self):
        self.xem.ActivateTriggerIn(PlusMaze.scope_settings['TRIG_EPADDR'],
                                   PlusMaze.scope_settings['trig_map']['reset'])
        time.sleep(0.1)
        frame_count = self.get_frame_count()
        print_msg("Reset miniscope counter (new value: {})".format(frame_count))

    def get_frame_count(self):
        self.xem.UpdateWireOuts()
        frame_lo = self.xem.GetWireOutValue(PlusMaze.scope_settings['FRAME_LO_EPADDR'])
        frame_hi = self.xem.GetWireOutValue(PlusMaze.scope_settings['FRAME_HI_EPADDR'])
        return ((frame_hi<<16) + frame_lo)

    def get_last_detected_pos(self):
        self.xem.UpdateWireOuts()
        last_detected_id = self.xem.GetWireOutValue(PlusMaze.prox_settings['LASTDETECT_EPADDR'])
        last_detected_id = last_detected_id & PlusMaze.prox_settings['LASTDETECT_MASK']
        last_detected_name = PlusMaze.prox_settings['names'][last_detected_id]
        return last_detected_name

    def get_lick_state(self):
        self.xem.UpdateWireOuts()
        status = self.xem.GetWireOutValue(PlusMaze.lick_settings['LICK_EPADDR'])
        return check_bit(status, PlusMaze.lick_settings['LICK_BIT'])

    def actuate_gate(self, gate, closed):
        val = PlusMaze.gate_settings[gate].cl if closed else PlusMaze.gate_settings[gate].op
        self.xem.SetWireInValue(PlusMaze.gate_settings[gate].epaddr, val)
        self.xem.UpdateWireIns()
        print_msg("{} gate {}".format(gate, "closed" if closed else "opened"))

    def dose(self, d):
        self.xem.ActivateTriggerIn(PlusMaze.dose_settings['TRIG_EPADDR'],
                                   PlusMaze.dose_settings[d].trig_bit)
        print_msg("Dosed {}".format(d))

    def compensate_turn(self, turn):
        self.rotate(PlusMaze.turn_compensation[turn])

    def rotate(self, r):
        self.xem.ActivateTriggerIn(PlusMaze.rotation_settings['TRIG_EPADDR'],
                                   PlusMaze.rotation_settings['trig_map'][r])
        print_msg("Rotating {}".format(r))

    def pull_lick_buffer(self):
        # First, reset the buffer read address counter
        self.xem.ActivateTriggerIn(PlusMaze.lick_settings['TRIG_EPADDR'],
                                   PlusMaze.lick_settings['trig_map']['reset_addr'])
        time.sleep(0.1)

        # Pull the buffer contents in binary. Note that contents are
        # stored little-endian
        bin_buf = bytearray(PlusMaze.lick_settings['BUFFER_LENGTH_IN_BYTES'])
        code = self.xem.ReadFromPipeOut(PlusMaze.lick_settings['PIPE_EPADDR'], bin_buf)
        if (code < 0):
            print_msg("WARNING: pull_lick_buffer failed!")
        else:
            print_msg("Transferred {} bytes from FPGA lickometer buffer".format(code))

        # Convert the binary buffer contents into list of bools, for readability
        buffer_length_in_bits = 8*PlusMaze.lick_settings['BUFFER_LENGTH_IN_BYTES']
        buf = [False,]*buffer_length_in_bits
        for i in xrange(PlusMaze.lick_settings['BUFFER_LENGTH_IN_BYTES']):
            bin_byte = bin_buf[i]
            for j in xrange(8):
                ind = 8*i + j
                buf[ind] = ((1<<j) & bin_byte == (1<<j))

        return buf
