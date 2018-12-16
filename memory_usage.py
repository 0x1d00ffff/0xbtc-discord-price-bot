

import sys

def rss_resource():
    """Return the resident set size of this process + its children in
    megabytes. NOTE: http://man7.org/linux/man-pages/man2/getrusage.2.html
    states that RUSAGE_CHILDREN reports only the size of the max child, not
    the sum of the process tree."""
    import resource
    rusage_denom = 1024.
    if sys.platform == 'darwin':
        # ... it seems that in OSX the output is different units ...
        rusage_denom = rusage_denom * rusage_denom
    mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / rusage_denom
    mem += resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / rusage_denom
    return mem

def rss_proc():
    """Memory usage of the current process in megabytes. Requires /proc
    in the filesystem."""
    status = None
    result = {'peak': 0, 'rss': 0}
    try:
        # This will only work on systems with a /proc file system
        # (like Linux).
        status = open('/proc/self/status')
        for line in status:
            parts = line.split()
            key = parts[0][2:-1].lower()
            if key in result:
                result[key] = int(parts[1])
    finally:
        if status is not None:
            status.close()
    return result['rss'] / 1024.0


if __name__ == "__main__":
    print('rss_resource:', rss_resource(), 'MB')
    print('rss_proc    :', rss_proc(), 'MB')


