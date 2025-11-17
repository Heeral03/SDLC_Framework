#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

bool isSafe(char **board, int size, int row, int col) {
    for (int i=0; i<col; i++) {
        if (board[row][i] == 'Q') {
            return false;
        }
    }

    for (int i=row, j=col; i<size && j>=0; i++, j--) {
        if (board[i][j] == 'Q') {
            return false;
        }
    }

    for (int i=row, j=col; i>=0 && j>=0; i--, j--) {
        if (board[i][j] == 'Q') {
            return false;
        }
    }

    return true;
}

void solveNQueens(char **board, int size, int col, int *solCount) {
    if (col == size) {
        printf("Solution %d:\n", (*solCount)++ + 1);
        for (int i=0; i<size; i++) {
            for (int j=0; j<size; j++) {
                printf("%c ", board[i][j]);
            }
            printf("\n");
        }

        return;
    }

    for (int i=0; i<size; i++) {
        if (isSafe(board, size, i, col)) {
            board[i][col] = 'Q';

            solveNQueens(board, size, col + 1, solCount);

            board[i][col] = '-';
        }
    }
}

int main() {
    int n;
    scanf("%d", &n);

    char **board = (char**)malloc(n*sizeof(char*));

    for (int i=0; i<n; i++) {
        board[i] = (char*)malloc(n*sizeof(char));

        for (int j=0; j<n; j++) {
            board[i][j] = '-';
        }
    }

    int solCount = 0;
    solveNQueens(board, n, 0, &solCount);   
    
    if (solCount == 0) {
        printf("No solutions found.\n");
    } else {
        printf("Number of solutions found: %d\n", solCount);
    } 

    for (int i=0; i<n; i++) {
        free(board[i]);
    }
    free(board);

    return 0;
}
