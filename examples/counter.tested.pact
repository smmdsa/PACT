pact 0.4
format "pact.module/0.3.0"
constants {"amount":7}
cells [{"id":"counter","values":[3],"mutable":true}]
fn step
params []
locals []
result "unit"
writes ["counter"]
z = 0
v = get counter z
a = const.load amount
sum = add.wrap v a
s = set counter z sum
return s
end
exports ["step"]
assets {"palettes":[],"tiles":[]}
presentation {}
tests [{"id":"step.baseline","function":"step","set":{},"expect":{"counter":[10]}}]
