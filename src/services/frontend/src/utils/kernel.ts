import { ServerConnection, Kernel } from "@jupyterlab/services";


const settings = ServerConnection.makeSettings(
        {baseUrl: "http://jh.data-sculptor.ru/hub"

});

export const listKernels = () => {
        Kernel.listRunning(settings).then(kernels => {
          console.log('Running kernels:', kernels);
        }).catch(err => {
          console.error('Failed to list kernels:', err);
        });
};