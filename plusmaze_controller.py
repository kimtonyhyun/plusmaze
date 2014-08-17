import wx

from plusmaze import PlusMaze

class PlusMazeController(wx.Frame):

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(275,3*120),
                          style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        self.pm = PlusMaze()

        # Set up GUI
        self._initialize_menu()

        self.Show(True)

    def _initialize_menu(self):
        menubar = wx.MenuBar()
        maze_menu = wx.Menu()

        # Maze options
        self.maintain_t_maze = maze_menu.Append(wx.ID_ANY,
                                         'Maintain T-maze',
                                         'Maintain T-maze',
                                         kind=wx.ITEM_CHECK)
        maze_menu.Check(self.maintain_t_maze.GetId(), True)

        # Autoreward options
        reward_menu = wx.Menu()
        self.reward_enable = reward_menu.Append(wx.ID_ANY,
                                                'Enable',
                                                'Enable',
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

        self.SetMenuBar(menubar)

    def on_exit(self, e):
        self.Close()

if (__name__ == '__main__'):
    app = wx.App(False)
    pmc = PlusMazeController(None, 'Plus Maze Controller')
    app.MainLoop()
