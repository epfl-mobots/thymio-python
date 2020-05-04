; Test assembly program for the Thymio
; Author: Yves Piguet, EPFL

    dc end_toc              ; total size of event handler table
    dc _ev.init, init       ; id and address of init event
end_toc:

init:                       ; code executed on init event
    push.s 0                ; push address of 3rd arg, stored somewhere in free memory
    store _userdata
    push.s _userdata
    push.s 32               ; push address of 2nd arg
    store _userdata+1
    push.s _userdata+1
    push.s 32               ; push address of 1st arg
    store _userdata+2
    push.s _userdata+2
    callnat _nf.leds.top    ; call native function to set top rgb led
    stop                    ; stop program
