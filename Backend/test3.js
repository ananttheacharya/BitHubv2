fetch('https://wandbox.org/api/compile.json', {
    method: 'POST', 
    headers: {'Content-Type': 'application/json'}, 
    body: JSON.stringify({
        compiler: 'gcc-head', 
        code: '#include <stdio.h>\nint main(){printf("Hello");return 0;}'
    })
}).then(r => r.json()).then(console.log).catch(console.error);
