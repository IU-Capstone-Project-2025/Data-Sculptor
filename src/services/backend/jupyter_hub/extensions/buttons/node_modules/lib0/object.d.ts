export function create(): {
    [x: string]: any;
};
/**
 * Object.assign
 */
export const assign: {
    <T extends {}, U>(target: T, source: U): T & U;
    <T_1 extends {}, U_1, V_1>(target: T_1, source1: U_1, source2: V_1): T_1 & U_1 & V_1;
    <T_2 extends {}, U_2, V_2, W>(target: T_2, source1: U_2, source2: V_2, source3: W): T_2 & U_2 & V_2 & W;
    (target: object, ...sources: any[]): any;
};
/**
 * @param {Object<string,any>} obj
 */
export const keys: {
    (o: object): string[];
    (o: {}): string[];
};
/**
 * @template V
 * @param {{[key:string]: V}} obj
 * @return {Array<V>}
 */
export const values: {
    <T>(o: {
        [s: string]: T;
    } | ArrayLike<T>): T[];
    (o: {}): any[];
};
export function forEach<V_1>(obj: {
    [k: string]: V_1;
}, f: (arg0: V_1, arg1: string) => any): void;
export function map<R>(obj: {
    [x: string]: any;
}, f: (arg0: any, arg1: string) => R): R[];
export function length(obj: {
    [x: string]: any;
}): number;
export function size(obj: {
    [x: string]: any;
}): number;
export function some(obj: {
    [x: string]: any;
}, f: (arg0: any, arg1: string) => boolean): boolean;
export function isEmpty(obj: Object | null | undefined): boolean;
export function every(obj: {
    [x: string]: any;
}, f: (arg0: any, arg1: string) => boolean): boolean;
export function hasProperty(obj: any, key: string | symbol): boolean;
export function equalFlat(a: {
    [x: string]: any;
}, b: {
    [x: string]: any;
}): boolean;
/**
 * Make an object immutable. This hurts performance and is usually not needed if you perform good
 * coding practices.
 */
export const freeze: {
    <T extends Function>(f: T): T;
    <T_1 extends {
        [idx: string]: object | U | null | undefined;
    }, U extends string | number | bigint | boolean | symbol>(o: T_1): Readonly<T_1>;
    <T_2>(o: T_2): Readonly<T_2>;
};
export function deepFreeze<T extends unknown>(o: T): Readonly<T>;
//# sourceMappingURL=object.d.ts.map