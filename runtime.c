
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define TAG_MASK 0xFFF8000000000000ULL
#define TAG_BASE 0x7FF8000000000000ULL
#define TAG_STRING 2ULL
#define TAG_ARRAY 3ULL
#define TAG_MAP 4ULL

typedef struct { uint64_t* data; size_t len; size_t cap; } Array;
typedef struct { uint64_t* keys; uint64_t* vals; size_t len; size_t cap; } Map;

int is_number(uint64_t v) { return (v & TAG_MASK) != TAG_BASE; }
double as_number(uint64_t v) { double d; memcpy(&d, &v, 8); return d; }
uint64_t get_tag(uint64_t v) { return (v >> 48) & 0x7; }
uint64_t as_index(uint64_t v) { return v & 0x0000FFFFFFFFFFFFULL; }

void print_value(uint64_t val) {
    if (is_number(val)) {
        double d = as_number(val);
        if (d == (long long)d) printf("%lld", (long long)d);
        else printf("%f", d);
    } else if (get_tag(val) == TAG_STRING) {
        printf("%s", (char*)as_index(val));
    } else if (get_tag(val) == TAG_ARRAY) {
        Array* arr = (Array*)as_index(val);
        printf("[");
        for (size_t i = 0; i < arr->len; i++) {
            print_value(arr->data[i]);
            if (i < arr->len - 1) printf(", ");
        }
        printf("]");
    } else if (get_tag(val) == TAG_MAP) {
        Map* map = (Map*)as_index(val);
        printf("{");
        for (size_t i = 0; i < map->len; i++) {
            print_value(map->keys[i]);
            printf(": ");
            print_value(map->vals[i]);
            if (i < map->len - 1) printf(", ");
        }
        printf("}");
    } else {
        printf("null");
    }
}

void donky_print(uint64_t val) {
    print_value(val);
    printf("\n");
}

uint64_t donky_alloc_string(const char* s) {
    char* copy = strdup(s);
    return TAG_BASE | (TAG_STRING << 48) | (uint64_t)copy;
}

uint64_t donky_alloc_array() {
    Array* arr = malloc(sizeof(Array));
    arr->data = NULL; arr->len = 0; arr->cap = 0;
    return TAG_BASE | (TAG_ARRAY << 48) | (uint64_t)arr;
}

void donky_array_push(uint64_t arr_val, uint64_t val) {
    Array* arr = (Array*)as_index(arr_val);
    if (arr->len == arr->cap) {
        arr->cap = arr->cap == 0 ? 4 : arr->cap * 2;
        arr->data = realloc(arr->data, arr->cap * sizeof(uint64_t));
    }
    arr->data[arr->len++] = val;
}

uint64_t donky_alloc_map() {
    Map* map = malloc(sizeof(Map));
    map->keys = NULL; map->vals = NULL; map->len = 0; map->cap = 0;
    return TAG_BASE | (TAG_MAP << 48) | (uint64_t)map;
}

void donky_map_set(uint64_t map_val, uint64_t key, uint64_t val) {
    Map* map = (Map*)as_index(map_val);
    for (size_t i = 0; i < map->len; i++) {
        if (map->keys[i] == key) {
            map->vals[i] = val;
            return;
        }
    }
    if (map->len == map->cap) {
        map->cap = map->cap == 0 ? 4 : map->cap * 2;
        map->keys = realloc(map->keys, map->cap * sizeof(uint64_t));
        map->vals = realloc(map->vals, map->cap * sizeof(uint64_t));
    }
    map->keys[map->len] = key;
    map->vals[map->len] = val;
    map->len++;
}

uint64_t donky_index_get(uint64_t target, uint64_t index) {
    if (get_tag(target) == TAG_ARRAY) {
        Array* arr = (Array*)as_index(target);
        size_t i = (size_t)as_number(index);
        if (i < arr->len) return arr->data[i];
    } else if (get_tag(target) == TAG_MAP) {
        Map* map = (Map*)as_index(target);
        for (size_t i = 0; i < map->len; i++) {
            if (map->keys[i] == index) return map->vals[i];
        }
    }
    return 0;
}

void donky_index_set(uint64_t target, uint64_t index, uint64_t val) {
    if (get_tag(target) == TAG_ARRAY) {
        Array* arr = (Array*)as_index(target);
        size_t i = (size_t)as_number(index);
        if (i < arr->len) arr->data[i] = val;
    } else if (get_tag(target) == TAG_MAP) {
        donky_map_set(target, index, val);
    }
}

int main() {
    extern void donky_main();
    donky_main();
    return 0;
}
