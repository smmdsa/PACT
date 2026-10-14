pact 0.2
format "pact.graph/0.0.1"
responsibility "greeting"
entry "emit"
effects ["stdout"]
text = utf8.literal "hola mundo, from an alien language\n"
emit = stdout.emit text
contracts [{"id":"exact","op":"stdout.exact","value":"hola mundo, from an alien language\n"}]
