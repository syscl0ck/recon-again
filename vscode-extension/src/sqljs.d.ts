declare module 'sql.js' {
    export interface Database {
        prepare(sql: string): Statement;
        exec(sql: string): QueryExecResult[];
        close(): void;
    }

    export interface Statement {
        bind(values: any[]): void;
        step(): boolean;
        getAsObject(): any;
        free(): void;
    }

    export interface QueryExecResult {
        columns: string[];
        values: any[][];
    }

    export default function initSqlJs(options?: any): Promise<{
        Database: new (data?: ArrayLike<number> | Buffer) => Database;
    }>;
}




