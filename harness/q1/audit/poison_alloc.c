/*
 * Q1 audit A4 dual-poison allocator for torch.cuda.memory.CUDAPluggableAllocator.
 *
 * Every allocation is filled with the byte in Q1_POISON_VALUE (0..255) before
 * PyTorch sees it, so an output buffer the kernel never writes keeps the
 * poison. Running a candidate once with 0x00 and once with 0xFF and comparing
 * outputs byte for byte exposes unwritten tails. Because this allocator
 * replaces the caching allocator, freed blocks are returned to the driver and
 * never handed back with stale contents.
 *
 * Build (in the cotcodec-q1-gates image):
 *   gcc -O2 -shared -fPIC -o libq1_poison_alloc.so poison_alloc.c \
 *       -I/usr/local/cuda/include -L/usr/local/cuda/lib64 -lcudart
 */
#include <stdlib.h>
#include <sys/types.h>
#include <cuda_runtime_api.h>

static int q1_poison_byte(void) {
    static int value = -1;
    if (value < 0) {
        const char *env = getenv("Q1_POISON_VALUE");
        int parsed = env ? atoi(env) : 0;
        value = (parsed < 0 || parsed > 255) ? 0 : parsed;
    }
    return value;
}

void *q1_poison_malloc(ssize_t size, int device, cudaStream_t stream) {
    void *ptr = NULL;
    int previous = 0;
    cudaGetDevice(&previous);
    if (previous != device) {
        cudaSetDevice(device);
    }
    if (cudaMalloc(&ptr, (size_t)size) != cudaSuccess) {
        ptr = NULL;
    } else if (size > 0) {
        cudaMemsetAsync(ptr, q1_poison_byte(), (size_t)size, stream);
        cudaStreamSynchronize(stream);
    }
    if (previous != device) {
        cudaSetDevice(previous);
    }
    return ptr;
}

void q1_poison_free(void *ptr, ssize_t size, int device, cudaStream_t stream) {
    (void)size;
    (void)stream;
    int previous = 0;
    cudaGetDevice(&previous);
    if (previous != device) {
        cudaSetDevice(device);
    }
    cudaFree(ptr);
    if (previous != device) {
        cudaSetDevice(previous);
    }
}
