# Chaos Mesh Pod-Kill Experiment

## Objective
Validate Kubernetes self-healing by injecting a pod-kill fault
into an isolated Nginx deployment using Chaos Mesh.

## Environment
- Kubernetes: kind cluster
- Chaos Mesh: v2.8.6
- Runtime: containerd
- Namespace: chaos-lab
- Workload: nginx:alpine
- Deployment: chaos-demo
- Initial replicas: 1

## Experiment
A PodChaos experiment named `chaos-demo-pod-kill` targeted
one pod with the label `app=chaos-demo`.

The experiment was accepted, and Chaos Mesh recorded successful
fault injection against the original pod.

## Observed Results
1. The original Nginx pod was killed.
2. The Kubernetes ReplicaSet created a replacement pod.
3. The replacement pod reached Running and Ready.
4. The deployment returned to 1/1 available replicas.
5. The PodChaos status initially remained Injected with
   AllRecovered=False.
6. During experiment deletion, Kubernetes events recorded
   successful chaos recovery and removal of the finalizer.
7. The PodChaos resource was deleted successfully.

## Conclusion
Pod-kill injection and Kubernetes deployment self-healing
were verified. The experiment's recovery status was initially
stale; successful recovery was subsequently recorded during
cleanup.

## Evidence
- `pod-kill-status.txt` — status captured before cleanup
- `pods-after-experiment.txt` — replacement pod details
- `deployment-recovery.txt` — deployment availability
- `experiment-events.txt` — injection, replacement, recovery,
  and cleanup events

## Limitations
The `/dev/fuse` access attempt in the Chaos Daemon logged a
device-cgroup error. This experiment validates pod-kill behavior
only; it does not establish that all Chaos Mesh experiment types
work in this environment.
