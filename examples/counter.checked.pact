pact 0.4
format "pact.module/0.4.0"
constants {"amount":7,"counter.before":3,"counter.after":10}
cells [{"id":"counter","values":[3],"mutable":true}]
fn step.checked
params []
locals []
result "unit"
writes ["counter"]
z = 0
v = get counter z
a = const.load amount
sum = add.wrap v a
s = set counter z sum
before = const.load counter.before
initial.matches = i32.eq v before
precondition = guard initial.matches s
after = const.load counter.after
final.matches = i32.eq v after
postcondition = assert final.matches
outcome = seq precondition postcondition
return outcome
end
exports ["step.checked"]
assets {"palettes":[],"tiles":[]}
presentation {}
tests [{"id":"step.from-3-to-10","function":"step.checked","set":{},"expect":{"counter":[10]}}]
