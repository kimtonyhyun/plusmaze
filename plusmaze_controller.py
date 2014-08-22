import os
import wx

from plusmaze import PlusMaze, DeviceError
from runtrials import RunTrialsDialog
from util import *

ID_EXPT_SEMIAUTO = wx.NewId()
ID_EXPT_EGOTRAIN = wx.NewId()

class PlusMazeController(wx.Frame):
    '''
    User interface for the plus maze
    '''

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(275,3*120),
                          style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        try:
            self.maze = PlusMaze()
        except DeviceError:
            wx.MessageBox('Error initializing the FPGA.\nSee console for detailed information.',
                          'PlusMazeController', wx.OK | wx.ICON_ERROR)
            self.Close()

        # Set up GUI
        self._initialize_menu()
        self._initialize_buttons()
        self.CreateStatusBar()
        self.StatusBar.SetFieldsCount(2)
        self.StatusBar.SetStatusWidths([-3, -1]) # Relative widths 3:1

        # Sample initial location of mouse (may be garbage)
        self.prev_pos = self.maze.get_last_detected_pos()
        print_msg("Initial detected position: {}".format(self.prev_pos))
        self.StatusBar.SetStatusText(self.prev_pos, 1)

        # Start polling of maze
        self.poll_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.default_polling , self.poll_timer)
        self.start_default_polling()

        self.Show(True)


    def _initialize_menu(self):
        menubar = wx.MenuBar()

        # Maze options
        maze_menu = wx.Menu()
        self.maintain_t_maze = maze_menu.Append(wx.ID_ANY,
                                         'Maintain T-maze',
                                         'Maintain T-maze',
                                         kind=wx.ITEM_CHECK)
        maze_menu.Check(self.maintain_t_maze.GetId(), True)

        # Autoreward options
        reward_menu = wx.Menu()
        self.reward_enable = reward_menu.Append(wx.ID_ANY,
                                                'Enable',
                                                'Enable autoreward',
                                                kind=wx.ITEM_CHECK)
        reward_menu.AppendSeparator()
        self.reward_every_arm = reward_menu.Append(wx.ID_ANY,
                                                   'Reward every arm entry',
                                                   'Reward every arm entry',
                                                   kind=wx.ITEM_RADIO)
        self.reward_right_turns = reward_menu.Append(wx.ID_ANY,
                                                     'Reward right turns',
                                                     'Reward right turns only',
                                                     kind=wx.ITEM_RADIO)
        self.reward_left_turns  = reward_menu.Append(wx.ID_ANY,
                                                     'Reward left turns',
                                                     'Reward left turns only',
                                                     kind=wx.ITEM_RADIO)
        maze_menu.AppendMenu(wx.ID_ANY, '&Autoreward', reward_menu)
        maze_menu.AppendSeparator()
        maze_menu.Append(wx.ID_EXIT, 'Exit', 'Exit the program')
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)
        menubar.Append(maze_menu, '&Maze')

        # Trial options
        expt_menu = wx.Menu()

        expt_menu.Append(ID_EXPT_EGOTRAIN, 'Continuous egocentric training', '')
        expt_menu.Append(ID_EXPT_SEMIAUTO, 'Semi-auto trials...', '')
        self.Bind(wx.EVT_MENU, self.run_semiauto_trials, id=ID_EXPT_SEMIAUTO)

        menubar.Append(expt_menu, '&Experiment')

        self.SetMenuBar(menubar)


    def _initialize_buttons(self):
        gs = wx.GridSizer(3,1)

        null_st = wx.StaticText(self, wx.ID_ANY, '')
        header_font = wx.Font(pointSize=12,
                              family=wx.DEFAULT,
                              style=wx.SLANT,
                              weight=wx.BOLD)

        # Gate
        gate_st = wx.StaticText(self, wx.ID_ANY, 'Gates:')
        gate_st.SetFont(header_font)

        gate_gs = wx.GridSizer(3,2)
        gate_gs.Add(gate_st, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL)
        gate_gs.Add(null_st, 0, wx.EXPAND)
        for d in PlusMaze.ordered_dirs:
            gate_btn = wx.ToggleButton(self, label=d)
            gate_btn.Bind(wx.EVT_TOGGLEBUTTON, self.actuate_gate)
            gate_gs.Add(gate_btn, 0, wx.EXPAND)
        
        gs.Add(gate_gs, 0, wx.EXPAND | wx.ALL, border=5)

        # Dosing
        dosing_st = wx.StaticText(self, wx.ID_ANY, 'Dosing:')
        dosing_st.SetFont(header_font)

        dosing_gs = wx.GridSizer(3,2)
        dosing_gs.Add(dosing_st, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL)

        for d in ['all',] + PlusMaze.ordered_dirs:
            dose_btn = wx.Button(self, label=d)
            dose_btn.Bind(wx.EVT_BUTTON, self.dose)
            dosing_gs.Add(dose_btn, 0, wx.EXPAND)

        gs.Add(dosing_gs, 0, wx.EXPAND | wx.ALL, border=5)

        # Rotation
        rotate_st = wx.StaticText(self, wx.ID_ANY, 'Rotation:')
        rotate_st.SetFont(header_font)

        rotate_gs = wx.GridSizer(3,2)
        rotate_gs.Add(rotate_st, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL)
        rotate_gs.Add(null_st, 0, wx.EXPAND)

        for r in ['center ccw', 'center cw', 'maze ccw', 'maze cw']:
            rot_btn = wx.Button(self, label=r)
            rot_btn.Bind(wx.EVT_BUTTON, self.rotate)
            rotate_gs.Add(rot_btn, 0, wx.EXPAND)

        gs.Add(rotate_gs, 0, wx.EXPAND | wx.ALL, border=5)

        self.SetSizer(gs)


    def start_default_polling(self):
        print_msg("Start default maze polling")
        self.poll_timer.Start(PlusMaze.POLL_PERIOD)


    def stop_default_polling(self):
        self.poll_timer.Stop()
        print_msg("Stopped default maze polling")


    def default_polling(self, e):
        pos = self.maze.get_last_detected_pos()
        if (self.prev_pos != pos):
            print "*"
            print_msg("Detected mouse at {}".format(pos))

            try:
                turn = PlusMaze.pos_to_turn[(self.prev_pos, pos)]
                print_msg("Mouse executed {} turn".format(turn))

                # Autoreward
                if self.reward_enable.IsChecked():
                    if self.reward_every_arm.IsChecked():
                        print_msg("Autoreward (every arm)")
                        self.maze.dose(pos)
                    elif (self.reward_right_turns.IsChecked() & (turn=='right')):
                        print_msg("Autoreward (right turn)")
                        self.maze.dose(pos)
                    elif (self.reward_left_turns.IsChecked() & (turn=='left')):
                        print_msg("Autoreward (left turn)")
                        self.maze.dose(pos)

                # Maintain T-maze
                if self.maintain_t_maze.IsChecked():
                    self.maze.rotate(PlusMaze.turn_compensation[turn])

            except KeyError, e:
                print_msg("Warning! Did the mouse jump over the T-block?")

        self.prev_pos = pos
        self.StatusBar.SetStatusText(self.prev_pos, 1)


    def actuate_gate(self, e):
        eo = e.EventObject
        gate = eo.GetLabel()
        closed = eo.GetValue()
        if closed:
            eo.SetBackgroundColour(wx.Colour(255,0,0))
        else:
            eo.SetBackgroundColour(wx.Colour(0,255,0))
        self.maze.actuate_gate(gate, closed)


    def dose(self, e):
        d = e.EventObject.GetLabel() # Direction, e.g. "west"
        self.maze.dose(d)


    def rotate(self, e):
        rot = e.EventObject.GetLabel()
        self.maze.rotate(rot)


    def run_semiauto_trials(self, e):
        self.stop_default_polling()

        # Select source file and run trials
        dlg = wx.FileDialog(self, "Choose trial file", '', '', '*.txt', wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            trial_file = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            runtrials_dlg = RunTrialsDialog(trial_file=trial_file,
                                            maze=self.maze,
                                            block_pos=self.prev_pos,
                                            parent=None, title='Run trials ({})'.format(trial_file))
            runtrials_dlg.ShowModal()
            self.last_pos = runtrials_dlg.block_pos # Retrieve final position of block
            runtrials_dlg.Destroy()

        self.start_default_polling()


    def on_exit(self, e):
        print "on_exit"
        self.Close()

if (__name__ == '__main__'):
    app = wx.App(False)
    pmc = PlusMazeController(None, 'Plus Maze Controller')
    app.MainLoop()
