pact 0.2
format "pact.module/0.1.0"
constants {}
cells [{"id":"counter","values":[2147483646,-2147483647],"mutable":true}]
fn advance
params ["index","amount"]
locals ["iteration"]
result "unit"
writes ["counter"]
index = local.get index
amount = local.get amount
value = get counter index
sum = add.wrap value amount
store = set counter index sum
repeat = flow.repeat 4 iteration store
return repeat
end
exports ["advance"]
assets {"palettes":[],"tiles":[]}
presentation {}
tests [{"id":"positive.wrap","function":"advance","args":[0,1],"set":{},"expect":{"counter":[-2147483646,-2147483647]}}]
