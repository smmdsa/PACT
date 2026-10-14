pact 0.4
format "pact.graph/0.0.1"
responsibility "demo.alien_greeting"
entry "e0"
effects ["stdout"]
v0 = "hola mundo, "
v1 = "from an alien language\n"
v2 = utf8.concat v0 v1
e0 = stdout.emit v2
contracts [{"id":"c0","op":"stdout.exact","value":"hola mundo, from an alien language\n"}]
