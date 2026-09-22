const fs = require('fs');
const VM = require('@scratch/scratch-vm');

const file = process.argv[2] || 'pen_chat.sb3';

function findVar(target, name) {
    for (const id in target.variables) {
        if (target.variables[id].name === name) return target.variables[id];
    }
    return null;
}

async function main() {
    const vm = new VM();
    await vm.loadProject(fs.readFileSync(file));
    vm.start();
    vm.greenFlag();

    const stage = vm.runtime.getTargetForStage();
    const sprite = vm.runtime.targets.find(t => !t.isStage);

    const send = findVar(stage, '☁ 送信');
    const recv = findVar(stage, '☁ 受信');
    const state = findVar(stage, '☁ 状態');
    const rowN = findVar(sprite, 'ROWN');
    const rowC = findVar(sprite, 'ROWC');
    const rowsVar = findVar(sprite, '行数');

    function report(label) {
        console.log(`[${label}] 送信=${send.value} 状態=${state.value} 行数=${rowsVar.value} ROWN=${JSON.stringify(rowN.value)} ROWC=${JSON.stringify(rowC.value)}`);
    }

    async function step(n) {
        for (let i = 0; i < n; i++) {
            vm.runtime._step();
            await Promise.resolve();
        }
    }

    await step(3);
    report('after greenflag');

    vm.runtime.emit('ANSWER', 'こんにちは');
    await Promise.resolve();
    await step(3);
    report('after answering ask (should be waiting for 状態=1)');

    state.value = '1';
    recv.value = 'R00010001108106200';
    await step(5);
    report('while thinking, echo pushed to 受信');

    await new Promise(r => setTimeout(r, 500));
    await step(5);
    console.log('timer after ~0.5s real time =', vm.runtime.ioDevices.clock.projectTimer());

    recv.value = 'R0002000220301010003110200';
    await step(5);
    report('reply chunk pushed to 受信 (still 状態=1)');

    state.value = '0';
    await step(5);
    report('状態=0 (done, ask loop should re-prompt)');

    vm.runtime.emit('ANSWER', 'はろー');
    await Promise.resolve();
    await step(5);
    report('after second answer');
}

main().then(() => process.exit(0)).catch(e => {
    console.error('FAIL', e);
    process.exit(1);
});
