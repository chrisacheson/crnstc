import std/[monotimes, os, times]

import engine
import ui

const fpsCap = 60
const minFrameTime =
  when fpsCap > 0: initDuration(seconds=1) div fpsCap
  else: initDuration()

when isMainModule:
  var gameEngine = newGameEngine()
  var userInterface = newUserInterface(gameEngine)
  var lastTime =
    when fpsCap > 0: getMonoTime()
    else: nil

  while not userInterface.quitRequested():
    userInterface.handleInput
    userInterface.render()

    when fpsCap > 0:
      let thisTime = getMonoTime()
      let frameTime = thisTime - lastTime

      if frameTime < minFrameTime:
        let delay = minFrameTime - frameTime
        sleep(delay.inMilliseconds)

  userInterface.quit()
