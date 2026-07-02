fetch('http://localhost:3001/api/practice/compile', {
    method: 'POST', 
    headers: {'Content-Type': 'application/json'}, 
    body: JSON.stringify({
        code: 'int sum(int a, int b) { return a + b; }', 
        problem: {
            evaluationType: 'return_value', 
            functionName: 'sum', 
            returnType: 'int', 
            testCases: [{input: [5, 10], expected_return: 15}]
        }
    })
}).then(r => r.json()).then(console.log).catch(console.error);
