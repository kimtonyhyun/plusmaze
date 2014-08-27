from __future__ import division

import wx

from plusmaze import PlusMaze
from util import *

class RunEgoTraining(wx.Dialog):
    '''
    Run continuous egocentric training
    '''
    def __init__(self, maze, prev_pos, *args, **kw):
        super(RunEgoTraining, self).__init__(*args, **kw)

        self.maze = maze
        self.prev_pos = prev_pos

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.setup = {'turn': wx.ComboBox(self, size=(60,-1), style=wx.CB_READONLY,
                                          choices=['left', 'right']),
                      'num_trials': wx.ComboBox(self, size=(60,-1), style=wx.CB_READONLY,
                                                choices=['10', '25', '50', '100', '200']),
                      'close_gate': wx.CheckBox(self, label='')
                     }
        
        # Set default values
        self.setup['turn'].SetValue('left')
        self.setup['num_trials'].SetValue('50')

        # Stats
        self.stats = {'trial_no': wx.StaticText(self, label=''),
                      'left':  wx.StaticText(self, label=''),
                      'right': wx.StaticText(self, label='')}

        self.controls = {'start':  wx.Button(self, label='Start'),
                         'pause':  wx.Button(self, label='Pause'),
                         'finish': wx.Button(self, label='Finish')}
        self.controls['start'].Enable()
        self.controls['pause'].Disable()
        self.controls['finish'].Disable()

        self.num_trials = 0 # Will be set later
        self.trial_index = 0
        self.num_left  = 0
        self.num_right = 0

        # Set up UI
        #------------------------------------------------------------
        self.SetSize((400,250))
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        alignment = wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL
        bval = 5
        bold_font = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.BOLD)

        # Setup
        setup_sb = wx.StaticBox(self, wx.ID_ANY, label='Setup')
        setup_sb.SetFont(bold_font)
        setup_sbs = wx.StaticBoxSizer(setup_sb, wx.VERTICAL)

        setup_gs = wx.GridSizer(3,2)
        setup_gs.AddMany([
            (wx.StaticText(self, wx.ID_ANY, 'Turn:'), 0, alignment, bval),
            (self.setup['turn'], 0, alignment, bval),
            (wx.StaticText(self, wx.ID_ANY, 'Num trials:'), 0, alignment, bval),
            (self.setup['num_trials'], 0, alignment, bval),
            (wx.StaticText(self, wx.ID_ANY, 'Close gate:'), 0, alignment, bval),
            (self.setup['close_gate'], 0, alignment, bval),
            ])
        setup_sbs.Add(setup_gs, 0, wx.EXPAND | wx.ALL, bval)
        hbox.Add(setup_sbs, 1, wx.ALL | wx.EXPAND, bval)

        # Overall stats
        overall_sb = wx.StaticBox(self, wx.ID_ANY, label='Overall stats')
        overall_sb.SetFont(bold_font)
        overall_sbs = wx.StaticBoxSizer(overall_sb, wx.VERTICAL)

        overall_gs = wx.GridSizer(3,2)
        overall_gs.AddMany([
            (wx.StaticText(self, wx.ID_ANY, 'Trial no.:'), 0, alignment, bval),
            (self.stats['trial_no'], 0, alignment, bval),
            (wx.StaticText(self, wx.ID_ANY, 'Left:'), 0, alignment, bval),
            (self.stats['left'], 0, alignment, bval),
            (wx.StaticText(self, wx.ID_ANY, 'Right:'), 0, alignment, bval),
            (self.stats['right'], 0, alignment, bval),
            ])
        overall_sbs.Add(overall_gs, 0, wx.EXPAND | wx.ALL, bval)
        hbox.Add(overall_sbs, 1, wx.ALL | wx.EXPAND, bval)

        vbox.Add(hbox, 1, wx.ALL | wx.EXPAND)

        # Controls
        alignment = alignment | wx.EXPAND

        control_sb = wx.StaticBox(self, wx.ID_ANY, label='Training control')
        control_sb.SetFont(bold_font)
        control_sbs = wx.StaticBoxSizer(control_sb, wx.HORIZONTAL)

        for c in ['start', 'pause', 'finish']:
            c_btn = self.controls[c]
            c_btn.Bind(wx.EVT_BUTTON, self._training_control)
            control_sbs.Add(c_btn, 1, alignment, bval)
        vbox.Add(control_sbs, 1, wx.ALL | wx.EXPAND, bval)

        self.SetSizer(vbox)

        self.sizers = {'overall': overall_gs}

        # Prepare maze monitor
        self.mon_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._monitor_training, self.mon_timer)

    def _update_stats(self):
        self.stats['trial_no'].SetLabel("{} ({:.0%})".format(
            self.trial_index, self.trial_index / self.num_trials))
        self.stats['left'].SetLabel("{} ({:.0%})".format(
            self.num_left, self.num_left / self.trial_index))
        self.stats['right'].SetLabel("{} ({:.0%})".format(
            self.num_right, self.num_right / self.trial_index))
        self.sizers['overall'].Layout()

    def _monitor_training(self, e):
        pos = self.maze.get_last_detected_pos()
        if (self.prev_pos != pos):
            print '* * * Trial {} of {} * * *'.format(self.trial_index, self.num_trials)
            print_msg('Detected mouse at {}'.format(pos))

            try:
                turn = PlusMaze.pos_to_turn[(self.prev_pos, pos)]
                print_msg('mouse executed {} turn'.format(turn))

                if (turn == self.setup['turn'].GetValue()):
                    print_msg("Reward for {} turn".format(turn))
                    self.maze.dose(pos)

                self.maze.compensate_turn(turn)

                # Keep tally
                if (turn == 'left'):
                    self.num_left += 1
                elif (turn == 'right'):
                    self.num_right += 1

                self._update_stats()

                if (self.trial_index == self.num_trials):
                    print_msg("Finished training sequence")
                    self.controls['start'].Disable()
                    self.controls['pause'].Disable()
                    self.controls['finish'].Enable()
                else:
                    self.trial_index += 1

                self.prev_pos = pos

            except KeyError, e:
                print_msg("Warning! Did the mouse jump over the T-block?")
                print_msg("Pausing training!")
                print_msg("Place the mouse back at {} before resuming training".format(
                            self.prev_pos))
                self._pause_training()


    def _training_control(self, e):
        ctrl = e.EventObject.GetLabel()
        if (ctrl == 'Start'):
            if (self.num_trials == 0):
                self._initialize_training()
            else:
                self._resume_training()
        elif (ctrl == 'Pause'):
            self._pause_training()
        elif (ctrl == 'Finish'):
            self._finish_training()


    def _initialize_training(self):
        self.controls['start'].Disable()
        self.controls['pause'].Enable()
        self.controls['finish'].Disable()

        # Can't alter training params once started
        self.setup['turn'].Disable()
        self.setup['num_trials'].Disable()
        self.setup['close_gate'].Disable()

        self.num_trials = int(self.setup['num_trials'].GetValue())
        self.trial_index = 1 # 1-index for the biologists

        self.mon_timer.Start(PlusMaze.POLL_PERIOD)


    def _resume_training(self):
        self.controls['start'].Disable()
        self.controls['pause'].Enable()
        self.controls['finish'].Disable()

        self.mon_timer.Start(PlusMaze.POLL_PERIOD)


    def _pause_training(self):
        self.controls['start'].Enable()
        self.controls['pause'].Disable()
        self.controls['finish'].Disable()

        self.mon_timer.Stop()


    def _finish_training(self):
        pass


    def OnClose(self, e):
        self.mon_timer.Stop()
        self.Destroy()
