import wx

from plusmaze import PlusMaze

class PlusMazeController(wx.Frame):

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(275,3*120),
                          style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        self.pm = PlusMaze()
        self.Show(True)

if (__name__ == '__main__'):
    app = wx.App(False)
    pmc = PlusMazeController(None, 'Plus Maze Controller')
    app.MainLoop()
