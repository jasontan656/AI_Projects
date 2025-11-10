// Initializes the single-node replica set used in local docker-compose.
const rsName = "rs0";
const adminDb = db.getSiblingDB("admin");
const replicaHost = process.env.MONGODB_REPLICA_SET_HOST || "mongo:27017";

function initiateReplicaSet() {
  const config = {
    _id: rsName,
    members: [{ _id: 0, host: replicaHost }],
  };
  const result = adminDb.runCommand({ replSetInitiate: config });
  printjson(result);
}

try {
  const status = adminDb.runCommand({ replSetGetStatus: 1 });
  if (status.ok === 1) {
    print("Replica set already initialized:");
    printjson(status.members.map((member) => ({ _id: member._id, name: member.name, stateStr: member.stateStr })));
    quit(0);
  }
} catch (error) {
  const message = error.message || "";
  if (message.includes("not running with --replSet")) {
    print("Skipping replica set initiation because mongod is running without --replSet (init phase).");
    quit(0);
  }
  if (error.codeName !== "NotYetInitialized") {
    print(`Unexpected error while checking replica set status: ${error}`);
    quit(1);
  }
}

initiateReplicaSet();
let ready = false;
for (let i = 0; i < 10; i++) {
  sleep(1000);
  try {
    const status = adminDb.runCommand({ replSetGetStatus: 1 });
    if (status.ok === 1) {
      ready = true;
      print("Replica set initiated and healthy.");
      printjson(status.members.map((member) => ({ _id: member._id, name: member.name, stateStr: member.stateStr })));
      break;
    }
  } catch (err) {
    print(`Waiting for replica set to become available: ${err}`);
  }
}

if (!ready) {
  print("Replica set did not become healthy within the expected time.");
  quit(1);
}
