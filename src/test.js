// Simple test to verify Windows CI is working
console.log('Windows CI test started');

function testAddition() {
    const result = 1 + 1;
    console.log(`1 + 1 = ${result}`);
    return result === 2;
}

// Run tests
const tests = [
    { name: 'Basic addition', test: testAddition }
];

let allPassed = true;
tests.forEach(({ name, test }) => {
    console.log(`\nRunning test: ${name}`);
    try {
        const result = test();
        console.log(`✅ ${name}: ${result ? 'PASSED' : 'FAILED'}`);
        if (!result) allPassed = false;
    } catch (error) {
        console.error(`❌ ${name}: ERROR`, error);
        allPassed = false;
    }
});

console.log('\nTest Summary:');
console.log(allPassed ? '✅ ALL TESTS PASSED' : '❌ SOME TESTS FAILED');

// Exit with appropriate code for CI
process.exit(allPassed ? 0 : 1);
