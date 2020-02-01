# RandRoll

None of the existing display configuration tools does what I think is "the right thing".
So I went and wrote one.

## The Right Thing

* Don't start from a stored config, use xrandr to read the systems' current state
* Allow creating "profiles" that will get applied smartly (not there yet)
* Generate a xrandr invocation to reflect the desired configuration
* Allow per-monitor scaling
* Allow arbitrary monitor positioning
* Implement "scale everything so all the pixels are the same size" (not done yet)

## To try:

If you have PySide2: `python -m xrandroll` in the folder where main.py is located.

## TODO:

* Implement other things
* Make it a proper app, with installation and whatnot
* Forget about it forever
