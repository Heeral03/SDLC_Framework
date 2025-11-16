#include <stdio.h>

int InsertionSort(int arr[], int n){
    int inversions = 0;
    for (int i = 0; i < n; i++){
        int key = arr[i];
        int j = i - 1;

        while (j >= 0 && arr[j] > key){
            arr[j+1] = arr[j];
            inversions++;
            j--;

        }
        arr[j+1] = key;
    }
    return inversions;
}


void main(){
    int n;
    printf("Enter n: ");
    scanf("%d", &n);
    int arr[n];

    printf("Enter elements of array:  ");
    for (int i = 0; i< n ; i++){
        scanf("%d ", &arr[i]);
    }
    InsertionSort(arr,n);
    for (int i = 0; i< n ; i++){
        printf("%d ", arr[i]);
    }

}