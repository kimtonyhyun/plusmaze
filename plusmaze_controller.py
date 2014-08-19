import wx

from plusmaze import PlusMaze, DeviceError

class PlusMazeController(wx.Frame):

    POLL_PERIOD = 250 # ms

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
        self.SetStatusText('hello',0)
        self.SetStatusText('bye',1)

        # Start polling of maze
        self.mon_timer = wx.Timer(self)
        self.mon_timer.Start(PlusMazeController.POLL_PERIOD)
        self.Bind(wx.EVT_TIMER, self.monitor, self.mon_timer)

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
                                                     'Reward right turns',
                                                     kind=wx.ITEM_RADIO)
        self.reward_left_turns  = reward_menu.Append(wx.ID_ANY,
                                                     'Reward left turns',
                                                     'Reward left turns',
                                                     kind=wx.ITEM_RADIO)
        maze_menu.AppendMenu(wx.ID_ANY, '&Autoreward', reward_menu)
        maze_menu.AppendSeparator()
        maze_menu.Append(wx.ID_EXIT, 'Exit', 'Exit the program')
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)
        menubar.Append(maze_menu, '&Maze')

        # Trial options
        trial_menu = wx.Menu()
        trial_menu.Append(wx.ID_OPEN, 'Select trial file...', 'Select trial file')
        self.Bind(wx.EVT_MENU, self.run_trials, id=wx.ID_OPEN)
        menubar.Append(trial_menu, '&Trials')

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

    def monitor(self, e):
        print "Poll"

    def actuate_gate(self, e):
        eo = e.EventObject
        gate = eo.GetLabel()
        closed = eo.GetValue()
        if closed:
            eo.SetBackgroundColour(wx.Colour(255,0,0))
        else:
            eo.SetBackgroundColour(wx.Colour(0,255,0))

    def dose(self, e):
        pass

    def rotate(self, e):
        pass
    
    def run_trials(self, e):
        pass

    def on_exit(self, e):
        print "on_exit"
        self.Close()

if (__name__ == '__main__'):
    app = wx.App(False)
    pmc = PlusMazeController(None, 'Plus Maze Controller')
    app.MainLoop()
