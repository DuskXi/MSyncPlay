import time

from loguru import logger

from song import Song

def test():
    logger.info("实例化测试")
    song = Song("PlayDataset.json")
    logger.info("添加测试")
    index = song.add_song("testList", "https://www.youtube.com/watch?v=fNuXZ17utvE&list=RDMMvFqRyP_uJ1I&index=30")
    logger.debug(f"测试结果: {index}")
    logger.info("重添加测试")
    index = song.add_song("testList", "https://www.youtube.com/watch?v=fNuXZ17utvE&list=RDMMvFqRyP_uJ1I&index=30")
    logger.debug(f"测试结果: {index}")
    logger.info("删除测试")
    result = song.remove_song("testList", index)
    logger.debug(f"结果: {result}，测试后: {song.playlists['testList']}")
    logger.info("列表添加测试")
    result = song.new_playlist("newList")
    logger.debug(f"测试结果: {result}")
    logger.info("列表删除测试")
    result = song.remove_playlist("newList")
    logger.debug(f"测试结果: {result}")
    logger.info("当前列表")
    result = song.get_current_playlist()
    logger.debug(f"结果: {result}")
    logger.info("当前歌曲")
    result = song.current()
    logger.debug(f"结果: {result}")
    logger.info("下一曲")
    result = song.next()
    logger.debug(f"结果: {result}")
    logger.info("上一曲")
    result = song.back()
    logger.debug(f"结果: {result}")
    time.sleep(1000 * 60)


if __name__ == '__main__':
    test()
