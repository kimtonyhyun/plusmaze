from __future__ import division

import collections
import os
import time
import wx

from plusmaze import PlusMaze
from util import *

Trial = collections.namedtuple('Trial', 'start goal result time')

class RunTrialsDialog(wx.Dialog):
    '''
    Run semi-automatic trials (the mouse needs to be handled -- removed
    and reinserted -- between trials)
    '''

    block_mappings = {('south', 'west') : ('center cw', 1),
                      ('south', 'north'): ('center cw', 2),
                      ('south', 'east') : ('center ccw', 1),
                      ('west',  'north'): ('center cw', 1),
                      ('west',  'east') : ('center cw', 2),
                      ('west',  'south'): ('center ccw', 1),
                      ('north', 'east' ): ('center cw', 1),
                      ('north', 'south'): ('center cw', 2),
                      ('north', 'west' ): ('center ccw', 1),
                      ('east',  'south'): ('center cw', 1),
                      ('east',  'west' ): ('center cw', 2),
                      ('east',  'north'): ('center ccw', 1)}

    def __init__(self, trial_file, maze, block_pos, *args, **kw):
        super(RunTrialsDialog, self).__init__(*args, **kw)

        self.trials = self._parse_trial_file(trial_file)
        self.num_trials = len(self.trials)
        print "{}: Loaded {} containing {} trials".format(
                get_time(), trial_file, self.num_trials)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.maze = maze
        self.block_pos = block_pos

        self.trial_index = 0
        self.trial_start = None
        self.trial_goal = None
        self.trial_time = None
        self.trial_result = None
        self.trial_start_time = None

        self.num_correct = 0

        self.trial_stats = {'trial_no': wx.StaticText(self, label=''),
                            'start_arm': wx.StaticText(self, label=''),
                            'goal_arm': wx.StaticText(self, label=''),
                            'result': wx.StaticText(self, label=''),
                            'time': wx.StaticText(self, label=''),
                           }

        self.overall_stats = {'num_correct': wx.StaticText(self, label=''),
                              'num_trials': wx.StaticText(self, label='{}'.format(self.num_trials)),
                              'percentage': wx.StaticText(self, label='')}

        self.controls = {'start':  wx.Button(self, label='Start'),
                         'rewind': wx.Button(self, label='Rewind'),
                         'finish': wx.Button(self, label='Finish')}
       
        # Set up UI
        #------------------------------------------------------------
        self.SetSize((400,300))
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        # Some "style"
        alignment = wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL
        bval = 5
        bold_font = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.BOLD)

        # Current trial
        current_sb = wx.StaticBox(self, wx.ID_ANY, label='Trial stats')
        current_sb.SetFont(bold_font)
        current_sbs = wx.StaticBoxSizer(current_sb, wx.VERTICAL)

        current_gs = wx.GridSizer(5,2)
        current_gs.AddMany([
            (wx.StaticText(self, -1, 'Trial #:'), 0, alignment, bval),
            (self.trial_stats['trial_no'], 0, alignment, bval),
            (wx.StaticText(self, -1, 'Start arm:'), 0, alignment, bval),
            (self.trial_stats['start_arm'], 0, alignment, bval),
            (wx.StaticText(self, -1, 'Goal arm:'), 0, alignment, bval),
            (self.trial_stats['goal_arm'], 0, alignment, bval),
            (wx.StaticText(self, -1, 'Time:'), 0, alignment, bval),
            (self.trial_stats['time'], 0, alignment, bval),
            (wx.StaticText(self, -1, 'Result:'), 0, alignment, bval),
            (self.trial_stats['result'], 0, alignment, bval),            
            ])
        
        current_sbs.Add(current_gs, 0, wx.EXPAND | wx.ALL, bval)
        hbox.Add(current_sbs, 1, wx.ALL | wx.EXPAND, bval)

        # All trials
        overall_sb = wx.StaticBox(self, wx.ID_ANY, label='Overall stats')
        overall_sb.SetFont(bold_font)
        overall_sbs = wx.StaticBoxSizer(overall_sb, wx.VERTICAL)
        
        overall_gs = wx.GridSizer(5,2)
        overall_gs.AddMany([
            (wx.StaticText(self, -1, 'Correct trials:'), 0, alignment, bval),
            (self.overall_stats['num_correct'], 0, alignment),
            (wx.StaticText(self, -1, 'Total trials:'), 0, alignment, bval),
            (self.overall_stats['num_trials'], 0, alignment),
            (wx.StaticText(self, -1, 'Running %:'), 0, alignment, bval),
            (self.overall_stats['percentage'], 0, alignment, bval),
            ])

        overall_sbs.Add(overall_gs, 0, wx.EXPAND | wx.ALL, bval)
        hbox.Add(overall_sbs, 1, wx.ALL | wx.EXPAND, bval)

        vbox.Add(hbox, 1, wx.ALL | wx.EXPAND)

        # Trial control
        alignment = alignment | wx.EXPAND
        
        control_sb = wx.StaticBox(self, wx.ID_ANY, label='Trial control')
        control_sb.SetFont(bold_font)
        control_sbs = wx.StaticBoxSizer(control_sb, wx.HORIZONTAL)

        for c in ['start', 'rewind', 'finish']:
            c_btn = self.controls[c]
            c_btn.Bind(wx.EVT_BUTTON, self._trial_control)
            control_sbs.Add(c_btn, 1, alignment, bval)
        vbox.Add(control_sbs, 1, wx.ALL | wx.EXPAND, bval)
        
        self.SetSizer(vbox)

        # Needed for layout after dynamically updating labels
        self.sizers = {'trial': current_gs,
                       'overall': overall_gs,
                      }

        # Prepare maze monitor
        #------------------------------------------------------------
        self.mon_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._monitor_trial, self.mon_timer)

        # Initialize first trial
        self._initialize_trial()


    def _parse_trial_file(self, trial_file):
        '''
        Trial files are text files where each line indicates the start and goal arms
        '''
        trials = []

        f = open(trial_file, 'r')
        for line in f:
            ld = line.split()
            trials.append(Trial(start=ld[0].lower(),
                                goal=ld[1].lower(),
                                result=None,
                                time=None))

        f.close()
        return trials


    def _initialize_trial(self):
        display_trial_index = str(self.trial_index + 1) # For the biologists
        print "*"
        print_msg("Initializing trial {}...".format(display_trial_index))

        # Set up trial stats
        trial = self.trials[self.trial_index]
        self.trial_stats['trial_no'].SetLabel(display_trial_index)
        self.trial_stats['start_arm'].SetLabel(trial.start)
        self.trial_stats['goal_arm'].SetLabel(trial.goal)
        self.trial_stats['time'].SetLabel('')
        self.trial_stats['result'].SetLabel('')
        self.sizers['trial'].Layout()

        # Actuate the maze
        for arm in PlusMaze.ordered_dirs:
            if (arm == trial.start):
                self.maze.actuate_gate(arm, True) # Close the gate
            else:
                self.maze.actuate_gate(arm, False)
        self._set_block_pos(trial.start)

        # Set up controls
        self.controls['start'].Enable()
        self.controls['rewind'].Disable()
        self.controls['finish'].Disable()

        # Prepare for polling
        self.trial_start = trial.start
        self.trial_goal = trial.goal
        
    def _set_block_pos(self, new_pos):
        if (self.block_pos == new_pos):
            return
        else:
            block_map = RunTrialsDialog.block_mappings[(self.block_pos, new_pos)]
            for i in xrange(block_map[1]):
                self.maze.rotate(block_map[0])
                time.sleep(1.5)
            self.block_pos = new_pos


    def _trial_control(self, e):
        ctrl = e.EventObject.GetLabel()
        if (ctrl == 'Start'):
            self._start_trial()
        elif (ctrl == 'Rewind'):
            self._rewind_trial()
        elif (ctrl == 'Finish'):
            self._finish_trial()


    def _start_trial(self):
        if (self.maze.get_last_detected_pos() != self.trial_start):
            print_msg("Error! Cannot start trial. Is the mouse in the start arm?")
        else:
            print_msg("Starting trial {}".format(self.trial_index+1)) # 1-index for biologists
            self.maze.actuate_gate(self.trial_start, False) # Open the gate
            self.trial_start_time = time.time()
            
            self.controls['start'].Disable()
            self.controls['rewind'].Enable()
            self.controls['finish'].Disable()

            self.mon_timer.Start(PlusMaze.POLL_PERIOD)

    def _monitor_trial(self, e):
        # Show elapsed time
        elapsed_time = time.time() - self.trial_start_time # sec
        m, s = divmod(elapsed_time, 60)
        self.trial_stats['time'].SetLabel("%02d:%02d" % (m, s))
        
        mouse_pos = self.maze.get_last_detected_pos()
        if (mouse_pos != self.trial_start):
            print_msg("Mouse detected at {}".format(mouse_pos))
            self.maze.actuate_gate(mouse_pos, True) # Close the gate
            self.trial_stats['result'].SetLabel(mouse_pos)

            if (mouse_pos == self.trial_goal):
                self.maze.dose(mouse_pos)

            self.trial_result = mouse_pos
            self.trial_time = elapsed_time
            
            self.mon_timer.Stop()
            self.controls['finish'].Enable()

        self.sizers['trial'].Layout()


    def _rewind_trial(self):
        print_msg("Re-setup trial {}".format(self.trial_index+1))
        self.mon_timer.Stop()
        self._initialize_trial()


    def _finish_trial(self):
        print_msg("Finish trial {}".format(self.trial_index+1))
        self.controls['rewind'].Disable()
        self.controls['finish'].Disable()
        
        # Record the result
        #   FIXME: May prefer a mutable representation of Trial
        new_trial = Trial(start=self.trials[self.trial_index].start,
                          goal=self.trials[self.trial_index].goal,
                          result=self.trial_result,
                          time=self.trial_time)
        self.trials[self.trial_index] = new_trial

        # Update running stats        
        if (self.trial_result == self.trial_goal):
            self.num_correct += 1
        self.overall_stats['num_correct'].SetLabel(str(self.num_correct))
        self.overall_stats['percentage'].SetLabel(
            "{:.0%}".format(self.num_correct/(self.trial_index+1)))
        self.sizers['overall'].Layout()

        # Move to next trial
        self.trial_index += 1
        if (self.trial_index < self.num_trials):
            self._initialize_trial()
        else:
            # We are done. Select output file and record results
            dlg = wx.FileDialog(self, "Choose output file", '', '', '*.txt',
                                wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
            if dlg.ShowModal() == wx.ID_OK:
                output_file = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
                self._save_result(output_file)


    def _save_result(self, output_file):
        print_msg("Writing results to {}...".format(output_file))
        f = open(output_file, 'w')
        for trial in self.trials:
            f.write("{} {} {} {}\n".format(trial.start, trial.goal, trial.result, trial.time))
        f.close()


    def OnClose(self, e):
        self.mon_timer.Stop()
        last_pos = self.maze.get_last_detected_pos()
        self._set_block_pos(last_pos)
        self.Destroy()
