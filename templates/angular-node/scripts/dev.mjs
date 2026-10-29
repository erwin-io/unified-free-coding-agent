import {spawn} from 'node:child_process';
const children = [];
const backend = spawn(process.execPath, ['backend/server.mjs'], {stdio:'inherit'});
children.push(backend);
const isWindows = process.platform === 'win32';
const command = isWindows ? 'cmd.exe' : 'npm';
const args = isWindows
  ? ['/d', '/s', '/c', 'npm --prefix frontend start -- --proxy-config proxy.conf.json']
  : ['--prefix','frontend','start','--','--proxy-config','proxy.conf.json'];
const frontend = spawn(command, args, {stdio:'inherit'});
children.push(frontend);
function shutDown(){
  for (const child of children) {
    if (child.exitCode === null) child.kill('SIGTERM');
  }
}
process.on('SIGINT', shutDown);
process.on('SIGTERM', shutDown);
for (const child of children) {
  child.on('exit', code => {
    if (code && code !== 0) process.exitCode = code;
    shutDown();
  });
}
