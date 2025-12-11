from ReaderWriter import ReaderWriter

def main():
    rw = ReaderWriter('data\\h5\\IDEAL_20-0055_EX_20230921T173256.h5', 'data\\h5\\out.h5')
    rw.convert()
    rw.close()

if __name__ == '__main__':
    main()
