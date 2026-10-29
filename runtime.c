
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
uint64_t make_number(double d) { uint64_t v; memcpy(&v, &d, 8); return v; }

void print_value(uint64_t val) {
    if (is_number(val)) {
        double d = as_number(val);
        if (d == (long long)d) printf("%lld", (long long)d);
        else printf("%g", d);
    } else if (get_tag(val) == TAG_STRING) {
        printf("\"%s\"", (char*)as_index(val)); // Print with quotes for JSON output
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

uint64_t donky_array_push(uint64_t arr_val, uint64_t val) {
    Array* arr = (Array*)as_index(arr_val);
    if (arr->len == arr->cap) {
        arr->cap = arr->cap == 0 ? 4 : arr->cap * 2;
        arr->data = realloc(arr->data, arr->cap * sizeof(uint64_t));
    }
    arr->data[arr->len++] = val;
    return 0;
}

uint64_t donky_alloc_map() {
    Map* map = malloc(sizeof(Map));
    map->keys = NULL; map->vals = NULL; map->len = 0; map->cap = 0;
    return TAG_BASE | (TAG_MAP << 48) | (uint64_t)map;
}

uint64_t donky_map_set(uint64_t map_val, uint64_t key, uint64_t val) {
    Map* map = (Map*)as_index(map_val);
    for (size_t i = 0; i < map->len; i++) {
        if (map->keys[i] == key) { map->vals[i] = val; return 0; }
    }
    if (map->len == map->cap) {
        map->cap = map->cap == 0 ? 4 : map->cap * 2;
        map->keys = realloc(map->keys, map->cap * sizeof(uint64_t));
        map->vals = realloc(map->vals, map->cap * sizeof(uint64_t));
    }
    map->keys[map->len] = key;
    map->vals[map->len] = val;
    map->len++;
    return 0;
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

uint64_t donky_index_set(uint64_t target, uint64_t index, uint64_t val) {
    if (get_tag(target) == TAG_ARRAY) {
        Array* arr = (Array*)as_index(target);
        size_t i = (size_t)as_number(index);
        if (i < arr->len) arr->data[i] = val;
    } else if (get_tag(target) == TAG_MAP) {
        donky_map_set(target, index, val);
    }
    return 0;
}

uint64_t donky_eq(uint64_t a, uint64_t b) {
    if (is_number(a) && is_number(b)) return make_number(as_number(a) == as_number(b) ? 1.0 : 0.0);
    if (get_tag(a) == TAG_STRING && get_tag(b) == TAG_STRING) {
        return make_number(strcmp((char*)as_index(a), (char*)as_index(b)) == 0 ? 1.0 : 0.0);
    }
    return make_number(a == b ? 1.0 : 0.0);
}

uint64_t donky_add(uint64_t a, uint64_t b) {
    if (is_number(a) && is_number(b)) {
        return make_number(as_number(a) + as_number(b));
    }
    if (get_tag(a) == TAG_STRING && get_tag(b) == TAG_STRING) {
        char* s1 = (char*)as_index(a);
        char* s2 = (char*)as_index(b);
        size_t len1 = strlen(s1);
        size_t len2 = strlen(s2);
        char* buf = malloc(len1 + len2 + 1);
        strcpy(buf, s1);
        strcat(buf, s2);
        return TAG_BASE | (TAG_STRING << 48) | (uint64_t)buf;
    }
    return 0;
}

uint64_t donky_byte_at(uint64_t s_val, uint64_t i_val) {
    if (get_tag(s_val) == TAG_STRING && is_number(i_val)) {
        char* s = (char*)as_index(s_val);
        size_t i = (size_t)as_number(i_val);
        if (i < strlen(s)) return make_number((double)(unsigned char)s[i]);
    }
    return make_number(-1.0);
}

uint64_t donky_substr(uint64_t s_val, uint64_t start_val, uint64_t end_val) {
    if (get_tag(s_val) != TAG_STRING) return 0;
    char* s = (char*)as_index(s_val);
    size_t start = (size_t)as_number(start_val);
    size_t end = (size_t)as_number(end_val);
    size_t len = strlen(s);
    
    if (start > len) start = len;
    if (end > len) end = len;
    if (start > end) start = end;
    
    size_t sub_len = end - start;
    char* buf = malloc(sub_len + 1);
    memcpy(buf, s + start, sub_len);
    buf[sub_len] = 0;
    
    return TAG_BASE | (TAG_STRING << 48) | (uint64_t)buf;
}

uint64_t donky_len(uint64_t val) {
    if (get_tag(val) == TAG_ARRAY) {
        return make_number((double)((Array*)as_index(val))->len);
    } else if (get_tag(val) == TAG_STRING) {
        return make_number((double)strlen((char*)as_index(val)));
    } else if (get_tag(val) == TAG_MAP) {
        return make_number((double)((Map*)as_index(val))->len);
    }
    return make_number(0.0);
}

uint64_t donky_push(uint64_t arr, uint64_t val) { return donky_array_push(arr, val); }

uint64_t donky_pop(uint64_t arr_val) {
    if (get_tag(arr_val) == TAG_ARRAY) {
        Array* arr = (Array*)as_index(arr_val);
        if (arr->len > 0) return arr->data[--arr->len];
    }
    return 0;
}

uint64_t donky_str(uint64_t val) {
    char buf[256];
    if (is_number(val)) {
        double d = as_number(val);
        if (d == (long long)d) sprintf(buf, "%lld", (long long)d);
        else sprintf(buf, "%g", d);
    } else if (get_tag(val) == TAG_STRING) {
        return val;
    } else if (get_tag(val) == TAG_ARRAY) { strcpy(buf, "[array]"); }
    else if (get_tag(val) == TAG_MAP) { strcpy(buf, "{map}"); }
    else { strcpy(buf, "null"); }
    return donky_alloc_string(buf);
}

uint64_t donky_num(uint64_t val) {
    if (is_number(val)) return val;
    if (get_tag(val) == TAG_STRING) return make_number(atof((char*)as_index(val)));
    return make_number(0.0);
}

uint64_t donky_read_file(uint64_t path_val) {
    if (get_tag(path_val) != TAG_STRING) return 0;
    FILE* f = fopen((char*)as_index(path_val), "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);
    char* buf = malloc(len + 1);
    fread(buf, 1, len, f);
    buf[len] = 0;
    fclose(f);
    uint64_t res = donky_alloc_string(buf);
    free(buf);
    return res;
}

int main() {
    extern void donky_toplevel();
    donky_toplevel();
    return 0;
}
