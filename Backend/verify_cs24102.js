const { queryDB } = require('./db');

async function compileAndRun(code, problem) {
    const response = await fetch('http://localhost:3000/api/practice/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, problem })
    });
    return response.json();
}

async function verifyAll() {
    console.log("Fetching all CS24102 problems...");
    const problems = await queryDB("SELECT JSON_ARRAYAGG(JSON_OBJECT('question_number', question_number, 'title', title, 'solutionCode', solutionCode, 'functionName', functionName, 'returnType', returnType, 'parameters', parameters, 'testCases', testCases, 'evaluationType', evaluationType)) FROM cs_problems");
    console.log(`Found ${problems.length} problems.`);
    
    let passCount = 0;
    let failCount = 0;
    const failures = [];

    for (const q of problems) {
        if (!q.solutionCode) {
            console.log(`[Q${q.question_number}] Skipping (no solution code)`);
            continue;
        }

        // Format problem for compile API
        const problem = {
            question_number: q.question_number,
            title: q.title,
            functionName: q.functionName || "solution",
            returnType: q.returnType || "void",
            parameters: q.parameters ? (typeof q.parameters === 'string' ? JSON.parse(q.parameters) : q.parameters) : [],
            testCases: q.testCases ? (typeof q.testCases === 'string' ? JSON.parse(q.testCases) : q.testCases) : [],
            evaluationType: q.evaluationType || "stdout"
        };

        try {
            const res = await compileAndRun(q.solutionCode, problem);
            
            if (res.success && !res.runError && res.runOutput && !res.runOutput.includes('[TEST_FAIL]')) {
                passCount++;
                console.log(`[Q${q.question_number}] PASS`);
            } else {
                failCount++;
                console.log(`[Q${q.question_number}] FAIL`);
                failures.push({
                    question_number: q.question_number,
                    title: q.title,
                    compileError: res.compileError,
                    runError: res.runError,
                    runOutput: res.runOutput
                });
            }
        } catch (e) {
            console.log(`[Q${q.question_number}] ERROR:`, e.message);
        }
    }

    console.log(`\nVerification Complete! Passed: ${passCount}, Failed: ${failCount}`);
    if (failures.length > 0) {
        console.log("Failures:");
        failures.forEach(f => {
            console.log(`- Q${f.question_number} (${f.title}):`);
            if (f.compileError) console.log(`  Compile Error: ${f.compileError}`);
            if (f.runError) console.log(`  Run Error: ${f.runError}`);
            if (f.runOutput && f.runOutput.includes('[TEST_FAIL]')) console.log(`  Run Output: ${f.runOutput}`);
        });
    }
}

verifyAll().catch(console.error).finally(() => process.exit(0));
