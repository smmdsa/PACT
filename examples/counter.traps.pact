pact 0.2
format "pact.module/0.5.0"
constants {"amount":7}
cells [{"id":"counter","values":[3],"mutable":true}]
fn step
params ["predicate"]
locals []
result "unit"
writes ["counter"]
z = i32.const 0
v = get counter z
a = const.load amount
sum = add.wrap v a
s = set counter z sum
p = local.get predicate
check = assert p
sequence = seq s check
return sequence
end
exports ["step"]
assets {"palettes":[],"tiles":[]}
presentation {}
tests [{"id":"success","function":"step","args":[1],"set":{},"expect":{"counter":[10]}},{"id":"reject-zero","function":"step","args":[0],"set":{},"expect":{"counter":[10]},"trap":{"code":"ASSERTION_FAILED","function":"step","node":"check"}},{"id":"writes-retained","function":"step","args":[0],"set":{"counter":[18]},"expect":{"counter":[25]},"trap":{"code":"ASSERTION_FAILED","function":"step","node":"check"}}]
