pact 0.4
format "pact.module/0.4.0"
constants {}
cells [{"id":"reserved","values":[0],"mutable":false}]
fn bounded.identity
params ["value"]
locals []
result "i32"
writes []
value = local.get value
zero = 0
nonnegative = i32.ge_s value zero
result = guard nonnegative value
return result
end
exports ["bounded.identity"]
assets {"palettes":[],"tiles":[]}
presentation {}
tests [{"id":"zero.allowed","function":"bounded.identity","args":[0],"set":{},"expect":{},"result":0},{"id":"positive.allowed","function":"bounded.identity","args":[7],"set":{},"expect":{},"result":7}]
